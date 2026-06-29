"""EDGAR ingestion and filing parsing — the core of edgar-alerts.

Discovery is **hybrid**:
  * EFTS full-text search over a date window (the workhorse: complete coverage,
    survives restarts via the overlapping lookback window), and
  * the ``getcurrent`` Atom feed (low-latency supplement for filings EFTS has
    not finished indexing yet).

Parsing handles two structurally different document families:
  * Form 4 ownership XML (``<ownershipDocument>``), and
  * the modern structured Schedule 13D/13G XML (``schedule13D`` namespace).

All HTTP goes through ``http_client`` (rate-limited, retrying, EDGAR UA).
"""
from __future__ import annotations

import datetime as dt
import logging
import re
import xml.etree.ElementTree as ET
from functools import lru_cache
from typing import Iterable, Optional

import config
import http_client as http
from models import Filing

log = logging.getLogger("edgar")

EFTS_URL = "https://efts.sec.gov/LATEST/search-index"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"
SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
GETCURRENT = "https://www.sec.gov/cgi-bin/browse-edgar"

# Map our internal codes back to the EFTS/getcurrent form tokens.
_TOKEN_FOR = {"4": "4", "13D": "SCHEDULE 13D", "13G": "SCHEDULE 13G"}


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def _efts_search(token: str, start: str, end: str) -> list[dict]:
    """Page through EFTS results for one form token in [start, end]."""
    out: list[dict] = []
    frm = 0
    while True:
        data = http.get_json(
            EFTS_URL,
            params={"forms": token, "startdt": start, "enddt": end, "from": frm},
        )
        if not data:
            break
        hits = data.get("hits", {}).get("hits", [])
        if not hits:
            break
        out.extend(hits)
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        frm += len(hits)
        if frm >= total or frm >= 9000:  # EFTS caps the window at 10k
            break
    return out


def _accession_from_link(link: str) -> Optional[str]:
    m = re.search(r"(\d{10}-\d{2}-\d{6})", link)
    if m:
        return m.group(1)
    m = re.search(r"/(\d{18})/", link + "/")
    if m:
        d = m.group(1)
        return f"{d[:10]}-{d[10:12]}-{d[12:]}"
    return None


def _getcurrent(token: str) -> list[dict]:
    """Best-effort low-latency feed. Returns minimal records; XML fills detail."""
    resp = http.get(
        GETCURRENT,
        params={
            "action": "getcurrent",
            "type": token,
            "owner": "include",
            "count": 100,
            "output": "atom",
        },
    )
    if resp is None:
        return []
    recs: list[dict] = []
    try:
        root = ET.fromstring(resp.content)
    except ET.ParseError:
        return []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
        link_el = entry.find("a:link", ns)
        href = link_el.get("href") if link_el is not None else ""
        acc = _accession_from_link(href or "")
        if not acc:
            continue
        cik_m = re.search(r"/data/(\d+)/", href)
        ciks = [cik_m.group(1)] if cik_m else []
        recs.append({"accession": acc, "ciks": ciks, "source": {}})
    return recs


def discover(start: str, end: str) -> list[dict]:
    """Return deduped filing records across all monitored forms.

    Each record: ``{accession, form_internal, ciks, filed_date, source}``.
    """
    by_acc: dict[str, dict] = {}
    for token, internal in config.EDGAR_FORMS.items():
        for hit in _efts_search(token, start, end):
            src = hit.get("_source", {})
            _id = hit.get("_id", "")
            acc = src.get("adsh") or _id.split(":")[0]
            if not acc:
                continue
            doc = _id.split(":", 1)[1] if ":" in _id else None
            by_acc.setdefault(
                acc,
                {
                    "accession": acc,
                    "form_internal": internal,
                    "ciks": [c.lstrip("0") or "0" for c in src.get("ciks", [])],
                    "filed_date": src.get("file_date"),
                    "doc": doc,
                    "source": src,
                },
            )
        # Low-latency supplement
        for rec in _getcurrent(token):
            acc = rec["accession"]
            if acc not in by_acc:
                rec.update({"form_internal": internal, "filed_date": None})
                by_acc[acc] = rec
    log.info("Discovered %d unique filings in %s..%s", len(by_acc), start, end)
    return list(by_acc.values())


# ---------------------------------------------------------------------------
# Document fetch
# ---------------------------------------------------------------------------
def _accnd(accession: str) -> str:
    return accession.replace("-", "")


def filing_index_url(cik: str, accession: str) -> str:
    return f"{ARCHIVES}/{int(cik)}/{_accnd(accession)}/"


def _fetch_doc(ciks: Iterable[str], accession: str, doc: str) -> Optional[str]:
    """Fetch a document, trying each associated CIK (EDGAR mirrors per filer)."""
    accnd = _accnd(accession)
    for cik in ciks:
        if not cik:
            continue
        resp = http.get(f"{ARCHIVES}/{int(cik)}/{accnd}/{doc}")
        if resp is not None:
            return resp.text
    return None


def _primary_doc_name(ciks: Iterable[str], accession: str) -> Optional[str]:
    """Find the primary document filename from the filing's index.json."""
    accnd = _accnd(accession)
    for cik in ciks:
        if not cik:
            continue
        data = http.get_json(f"{ARCHIVES}/{int(cik)}/{accnd}/index.json")
        if not data:
            continue
        items = data.get("directory", {}).get("item", [])
        # Prefer a *.xml that isn't an XBRL/exhibit sidecar.
        xmls = [i["name"] for i in items if i.get("name", "").endswith(".xml")]
        for name in xmls:
            low = name.lower()
            if low == "primary_doc.xml" or low.startswith("form") or "ownership" in low:
                return name
        if xmls:
            return xmls[0]
    return None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _text(el: Optional[ET.Element], path: str, ns: Optional[dict] = None) -> str:
    if el is None:
        return ""
    found = el.find(path, ns) if ns else el.find(path)
    return (found.text or "").strip() if found is not None and found.text else ""


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _role_from_relationship(rel: ET.Element) -> tuple[str, str]:
    """Return (insider_title_for_scoring, short_role_label)."""
    is_dir = _text(rel, "isDirector") in ("1", "true")
    is_off = _text(rel, "isOfficer") in ("1", "true")
    is_ten = _text(rel, "isTenPercentOwner") in ("1", "true")
    title = _text(rel, "officerTitle")
    if is_off and title:
        return title, title
    if is_ten:
        return "10% Owner", "10% Owner"
    if is_dir:
        return "Director", "Director"
    if is_off:
        return "Officer", "Officer"
    return "Other", "Insider"


def parse_form4(xml: str, rec: dict) -> Optional[Filing]:
    """Parse a Form 4 into a single Filing aggregating its P-code purchases.

    A joint Form 4 lists transactions once for all reporting owners, so we emit
    one Filing per accession (not per owner) to avoid multiplying trade value,
    and pick the most senior role across the owners.
    """
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError as exc:
        log.warning("Form4 XML parse error %s: %s", rec["accession"], exc)
        return None

    issuer = root.find("issuer")
    issuer_cik = _text(issuer, "issuerCik")
    issuer_name = _text(issuer, "issuerName")
    ticker = _clean_ticker(_text(issuer, "issuerTradingSymbol"))

    # Most senior role across all reporting owners; remember the first owner CIK.
    best_rank, best_title, best_label = -1, "Other", "Insider"
    owner_cik = None
    owner_name = ""
    rank = {"chief executive": 6, "ceo": 6, "chief financial": 5, "cfo": 5,
            "president": 4, "chief operating": 4, "coo": 4, "10% owner": 3,
            "director": 2, "officer": 1, "other": 0}
    for ro in root.findall("reportingOwner"):
        if owner_cik is None:
            owner_cik = _text(ro, "reportingOwnerId/rptOwnerCik")
            owner_name = _text(ro, "reportingOwnerId/rptOwnerName")
        rel = ro.find("reportingOwnerRelationship")
        if rel is None:
            continue
        title, label = _role_from_relationship(rel)
        r = rank.get(title.lower(), 0)
        if "chief executive" in title.lower():
            r = 6
        if r > best_rank:
            best_rank, best_title, best_label = r, title, label

    # Aggregate open-market purchases (transaction code "P").
    total_shares = 0.0
    weighted_cost = 0.0
    latest_date = None
    table = root.find("nonDerivativeTable")
    if table is None:
        return None  # purchases live in the non-derivative table
    for txn in table.findall("nonDerivativeTransaction"):
        code = _text(txn, "transactionCoding/transactionCode")
        if code != "P":
            continue
        shares = _to_float(_text(txn, "transactionAmounts/transactionShares/value"))
        price = _to_float(_text(txn, "transactionAmounts/transactionPricePerShare/value"))
        if shares is None or price is None:
            continue
        total_shares += shares
        weighted_cost += shares * price
        tdate = _text(txn, "transactionDate/value")
        if tdate and (latest_date is None or tdate > latest_date):
            latest_date = tdate

    if total_shares <= 0:
        return None  # no open-market purchase → filtered out

    avg_price = weighted_cost / total_shares
    trade_value = weighted_cost

    # 10b5-1: post-2023 forms carry a structured flag; older ones note it in a
    # footnote. Heuristic: explicit flag, else a footnote mentioning a plan.
    is_10b5 = _detect_10b5_1(root, xml)

    return Filing(
        accession=rec["accession"],
        filing_type="4",
        form_raw=rec.get("source", {}).get("form", "4"),
        filing_url=filing_index_url(issuer_cik or (rec["ciks"][0] if rec["ciks"] else "0"), rec["accession"]),
        filed_date=rec.get("filed_date") or "",
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        ticker=ticker,
        owner_cik=owner_cik,
        filer_name=owner_name,
        insider_title=best_title,
        role_label=best_label,
        transaction_code="P",
        trade_price=round(avg_price, 4),
        shares=total_shares,
        trade_value=trade_value,
        trade_date=latest_date,
        is_10b5_1=is_10b5,
    )


def _detect_10b5_1(root: ET.Element, raw: str) -> bool:
    for el in root.iter():
        if "10b5" in _localname(el.tag).lower():
            if (el.text or "").strip().lower() in ("1", "true", "yes"):
                return True
    low = raw.lower()
    return "10b5-1" in low and "plan" in low


def parse_schedule13(xml: str, rec: dict) -> Optional[Filing]:
    """Parse a structured Schedule 13D/13G primary_doc.xml."""
    try:
        root = ET.fromstring(xml.encode("utf-8"))
    except ET.ParseError as exc:
        log.warning("13D/G XML parse error %s: %s", rec["accession"], exc)
        return None

    def find_local(name: str) -> Optional[ET.Element]:
        for el in root.iter():
            if _localname(el.tag) == name:
                return el
        return None

    submission_type = (find_local("submissionType").text or "").strip() if find_local("submissionType") is not None else ""
    is_amendment = "/A" in submission_type or find_local("previousAccessionNumber") is not None
    filing_type = "13D" if "13D" in submission_type else "13G"

    issuer_cik = ""
    issuer_name = ""
    issuer_info = find_local("issuerInfo")
    if issuer_info is not None:
        for el in issuer_info.iter():
            ln = _localname(el.tag)
            if ln == "issuerCIK" and el.text:
                issuer_cik = el.text.strip()
            elif ln == "issuerName" and el.text:
                issuer_name = el.text.strip()

    # Highest percent-of-class reported across all reporting persons.
    pct = None
    for el in root.iter():
        if _localname(el.tag) == "percentOfClass" and el.text:
            v = _to_float(el.text)
            if v is not None:
                pct = v if pct is None else max(pct, v)

    # Names from the EFTS hit (filer name is not cleanly in the 13D XML body).
    names = rec.get("source", {}).get("display_names", [])
    filer_name = names[0].split("(CIK")[0].strip() if names else ""
    if not issuer_name and names:
        issuer_name = names[-1].split("(CIK")[0].strip()

    return Filing(
        accession=rec["accession"],
        filing_type=filing_type,
        form_raw=submission_type or filing_type,
        filing_url=filing_index_url(issuer_cik or (rec["ciks"][0] if rec["ciks"] else "0"), rec["accession"]),
        filed_date=rec.get("filed_date") or "",
        issuer_cik=issuer_cik,
        issuer_name=issuer_name,
        filer_name=filer_name,
        owner_cik=rec["ciks"][0] if rec["ciks"] else None,
        insider_title=filer_name,
        role_label=filing_type,
        percent_of_class=pct,
        is_amendment=is_amendment,
        is_new_position=(filing_type == "13D" and not is_amendment),
        filer_kind=_classify_filer(filer_name),
    )


def _classify_filer(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ("fund", "capital", "partners", "management", "advisors", "asset")):
        return "fund"
    if any(k in n for k in ("inc", "corp", "co.", "company", "holdings", "ltd", "llc", "group")):
        return "corporation"
    return "individual"


def parse_filing(rec: dict) -> Optional[Filing]:
    """Fetch the primary document for a record and parse it to a Filing."""
    ciks = rec.get("ciks") or []
    doc = rec.get("doc")
    if rec["form_internal"] == "4":
        if not doc:
            doc = _primary_doc_name(ciks, rec["accession"])
        if not doc:
            return None
        xml = _fetch_doc(ciks, rec["accession"], doc)
        return parse_form4(xml, rec) if xml else None
    else:  # 13D / 13G
        xml = _fetch_doc(ciks, rec["accession"], "primary_doc.xml")
        if not xml:
            doc = _primary_doc_name(ciks, rec["accession"])
            xml = _fetch_doc(ciks, rec["accession"], doc) if doc else None
        return parse_schedule13(xml, rec) if xml else None


# ---------------------------------------------------------------------------
# Enrichment via the issuer/insider submissions API
# ---------------------------------------------------------------------------
@lru_cache(maxsize=512)
def _submissions(cik: str) -> Optional[dict]:
    if not cik:
        return None
    return http.get_json(SUBMISSIONS.format(cik=str(int(cik)).zfill(10)))


def _days_since_last_8k(issuer_cik: str, as_of: dt.date) -> int:
    data = _submissions(issuer_cik)
    if not data:
        return 9999
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    for form, date in zip(forms, dates):
        if form.startswith("8-K"):
            try:
                d = dt.date.fromisoformat(date)
            except ValueError:
                continue
            if d <= as_of:
                return (as_of - d).days
    return 9999


def _ticker_for(cik: str) -> Optional[str]:
    data = _submissions(cik)
    if data and data.get("tickers"):
        return data["tickers"][0]
    return None


def _cluster_count(issuer_cik: str, trade_date: dt.date, exclude_acc: str) -> int:
    """Count P-code Form 4 accessions at this issuer within ±5 days."""
    data = _submissions(issuer_cik)
    if not data:
        return 0
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    count = 0
    for form, date, acc in zip(forms, dates, accs):
        if form != "4" or acc == exclude_acc:
            continue
        try:
            d = dt.date.fromisoformat(date)
        except ValueError:
            continue
        if abs((d - trade_date).days) <= 5:
            count += 1
    return count


def _is_first_open_market_purchase(owner_cik: str, issuer_cik: str, as_of: dt.date) -> bool:
    """True if this owner has no other Form 4 at this issuer in the prior 12 months."""
    data = _submissions(owner_cik)
    if not data:
        return False
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    cutoff = as_of - dt.timedelta(days=365)
    prior = 0
    for form, date in zip(forms, dates):
        if form != "4":
            continue
        try:
            d = dt.date.fromisoformat(date)
        except ValueError:
            continue
        if cutoff <= d < as_of:
            prior += 1
    return prior == 0


def enrich(filing: Filing) -> None:
    """Fill EDGAR-derived signals (8-K gap, cluster, first-purchase, ticker)."""
    try:
        as_of = dt.date.fromisoformat(filing.filed_date) if filing.filed_date else dt.date.today()
    except ValueError:
        as_of = dt.date.today()

    if not filing.ticker and filing.issuer_cik:
        filing.ticker = _ticker_for(filing.issuer_cik)

    if filing.issuer_cik:
        filing.days_since_last_8k = _days_since_last_8k(filing.issuer_cik, as_of)

    if filing.filing_type == "4":
        td = None
        if filing.trade_date:
            try:
                td = dt.date.fromisoformat(filing.trade_date)
            except ValueError:
                td = None
        td = td or as_of
        filing.days_since_trade = (dt.date.today() - td).days
        if filing.issuer_cik:
            filing.cluster_count = _cluster_count(filing.issuer_cik, td, filing.accession)
        if filing.owner_cik and filing.issuer_cik:
            filing.is_first_open_market_purchase = _is_first_open_market_purchase(
                filing.owner_cik, filing.issuer_cik, as_of
            )


def _clean_ticker(raw: str) -> Optional[str]:
    """Normalise placeholder trading symbols ('N/A', 'NONE', '') to None."""
    t = (raw or "").strip().upper()
    if not t or t in ("N/A", "NONE", "NA", "-"):
        return None
    return t


def _to_float(s) -> Optional[float]:
    try:
        return float(str(s).replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return None

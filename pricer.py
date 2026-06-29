"""Market data: current price, market cap, and trade-to-now price delta.

Primary source is yfinance. Because ``yfinance`` is rate-limited and often
returns partial data, market cap falls back to EDGAR XBRL shares-outstanding
times the current price. Results are cached per ticker for the life of a scan
to avoid hammering either provider.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

import http_client as http
from models import Filing

log = logging.getLogger("edgar.pricer")

COMPANYFACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"


@lru_cache(maxsize=1024)
def _quote(ticker: str) -> tuple[Optional[float], Optional[float]]:
    """Return (last_price, market_cap) for a ticker, or (None, None)."""
    try:
        import yfinance as yf
    except ImportError:
        log.error("yfinance not installed")
        return None, None
    try:
        t = yf.Ticker(ticker)
        price = mcap = None
        try:
            fi = t.fast_info
            price = _num(getattr(fi, "last_price", None)) or _num(fi.get("lastPrice") if hasattr(fi, "get") else None)
            mcap = _num(getattr(fi, "market_cap", None)) or _num(fi.get("marketCap") if hasattr(fi, "get") else None)
        except Exception:  # fast_info is flaky
            pass
        if price is None or mcap is None:
            info = t.info or {}
            price = price or _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice"))
            mcap = mcap or _num(info.get("marketCap"))
        return price, mcap
    except Exception as exc:  # network/parse/ratelimit
        log.warning("yfinance lookup failed for %s: %s", ticker, exc)
        return None, None


@lru_cache(maxsize=1024)
def _shares_outstanding_xbrl(cik: str) -> Optional[float]:
    """Most recent reported common shares outstanding from XBRL companyfacts."""
    if not cik:
        return None
    data = http.get_json(COMPANYFACTS.format(cik=str(int(cik)).zfill(10)))
    if not data:
        return None
    facts = data.get("facts", {})
    for taxonomy in ("dei", "us-gaap"):
        concept = facts.get(taxonomy, {}).get("EntityCommonStockSharesOutstanding")
        if not concept:
            continue
        units = concept.get("units", {})
        best = None
        for series in units.values():
            for pt in series:
                val, end = pt.get("val"), pt.get("end")
                if val and end and (best is None or end > best[1]):
                    best = (val, end)
        if best:
            return float(best[0])
    return None


def attach_market_data(filing: Filing) -> None:
    """Populate market_cap, current_price, and price_delta_pct on the filing."""
    if not filing.ticker:
        return
    price, mcap = _quote(filing.ticker)
    filing.current_price = price

    if mcap is None and price is not None and filing.issuer_cik:
        shares = _shares_outstanding_xbrl(filing.issuer_cik)
        if shares:
            mcap = shares * price
            log.debug("mcap for %s via XBRL fallback: %.0f", filing.ticker, mcap)
    filing.market_cap = mcap

    # Form 4: signed % move from the insider's entry to now.
    if filing.filing_type == "4" and price and filing.trade_price:
        filing.price_delta_pct = (price - filing.trade_price) / filing.trade_price * 100

    # 13D/13G have no single trade price; approximate aggregate value from the
    # reported ownership percentage so the relative-size axis can still score.
    if filing.filing_type in ("13D", "13G") and filing.trade_value is None:
        if filing.percent_of_class and mcap:
            filing.trade_value = mcap * filing.percent_of_class / 100.0


def _num(v) -> Optional[float]:
    try:
        if v is None:
            return None
        f = float(v)
        return f if f > 0 else None
    except (ValueError, TypeError):
        return None

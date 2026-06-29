"""Shared data structures passed between the EDGAR parser, scorer, and notifier."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Filing:
    """A single scorable insider event.

    One EDGAR accession can produce multiple ``Filing`` objects — e.g. a Form 4
    with several reporting owners yields one per owner — so dedup is keyed on
    ``(accession, owner_cik)`` while the accession is what we record as seen.
    """

    # Identity
    accession: str                     # e.g. "0001234567-26-000123"
    filing_type: str                   # "4" | "13D" | "13G"
    form_raw: str                      # raw EDGAR form string (may include "/A")
    filing_url: str                    # human-readable EDGAR filing index URL
    filed_date: str                    # YYYY-MM-DD

    # Issuer (target company)
    issuer_cik: str
    issuer_name: str
    ticker: Optional[str] = None

    # Filer / insider
    owner_cik: Optional[str] = None
    filer_name: str = ""
    insider_title: str = ""            # raw role text used by the scorer
    role_label: str = ""               # short label for the SMS, e.g. "CEO"

    # Form 4 transaction details
    transaction_code: Optional[str] = None   # "P", "S", "A", ...
    trade_price: Optional[float] = None       # $ per share
    shares: Optional[float] = None
    trade_value: Optional[float] = None       # $ = shares * price (or 13D aggregate)
    trade_date: Optional[str] = None          # YYYY-MM-DD
    is_10b5_1: bool = False

    # 13D/13G details
    percent_of_class: Optional[float] = None
    is_amendment: bool = False
    is_new_position: bool = False             # 13D original (not /A)
    filer_kind: str = ""                      # "corporation" | "individual" | "fund"

    # Enrichment (filled by pricer + edgar enrichment)
    market_cap: Optional[float] = None
    current_price: Optional[float] = None
    price_delta_pct: Optional[float] = None
    days_since_last_8k: int = 9999
    days_since_trade: Optional[int] = None
    cluster_count: int = 0                     # other P-code Form 4s ±5d same issuer
    is_first_open_market_purchase: bool = False

    # Scoring output
    score: int = 0
    breakdown: dict = field(default_factory=dict)

    @property
    def rel_pct(self) -> Optional[float]:
        if self.trade_value and self.market_cap:
            return (self.trade_value / self.market_cap) * 100
        return None

    @property
    def dedup_key(self) -> str:
        return f"{self.accession}:{self.owner_cik or '_'}"

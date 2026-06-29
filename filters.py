"""Hard filters applied before scoring. A filing failing any check is dropped.

Split into two stages so we only spend a market-data lookup on filings that
already pass the cheap structural checks:

* ``prefilter`` — form type, open-market purchase, trade value, 10b5-1. No
  network needed (uses already-parsed fields).
* ``market_filter`` — market-cap ceiling (needs the pricer to have run).
"""
from __future__ import annotations

from typing import Optional

import config
from models import Filing


def prefilter(filing: Filing) -> Optional[str]:
    """Return a rejection reason, or None if the filing passes."""
    if filing.filing_type not in ("4", "13D", "13G"):
        return f"unsupported form {filing.filing_type}"

    if filing.filing_type == "4":
        if filing.transaction_code != "P":
            return f"transaction code {filing.transaction_code} (not open-market purchase)"
        if filing.is_10b5_1:
            return "10b5-1 pre-scheduled plan"
        if not filing.trade_value or filing.trade_value < config.MIN_TRADE_VALUE:
            return f"trade value ${filing.trade_value or 0:,.0f} < ${config.MIN_TRADE_VALUE:,}"
    return None


def market_filter(filing: Filing) -> Optional[str]:
    """Return a rejection reason based on market data, or None if it passes."""
    if filing.market_cap is None:
        return "market cap unavailable (could not price ticker)"
    if filing.market_cap > config.MAX_MARKET_CAP:
        return f"market cap ${filing.market_cap:,.0f} > ${config.MAX_MARKET_CAP:,}"
    # For 13D/13G the trade value is approximated from ownership %; still enforce
    # the floor so trivial positions don't alert.
    if filing.trade_value and filing.trade_value < config.MIN_TRADE_VALUE:
        return f"position value ${filing.trade_value:,.0f} < ${config.MIN_TRADE_VALUE:,}"
    return None

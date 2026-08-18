"""Candidate universes.

`LIQUID_2004` is the default for long backtests. It is a list of US large
caps that were already large and liquid in 2004, so a 2005+ backtest is
not choosing its stocks based on what happened after 2005. That removes
most -- but not all -- selection bias: every name here still trades in
2026, so outright bankruptcies of the era (Lehman, Washington Mutual,
General Motors' old shares, Circuit City) are absent. Returns from any
backtest on this universe should be read as somewhat optimistic. See
README for the size of that effect.

`MODERN_ADDITIONS` covers names that only became liquid later. Include
them for recent-window scans, exclude them from long backtests.
"""

from __future__ import annotations

from pathlib import Path

BENCHMARK = "SPY"

LIQUID_2004 = [
    "AAPL", "ABT", "ADBE", "ADI", "ADM", "AEP", "AES", "AFL", "AIG", "ALL",
    "AMAT", "AMD", "AMGN", "AON", "APA", "APD", "AXP", "BA", "BAC", "BAX",
    "BBY", "BDX", "BEN", "BK", "BMY", "BSX", "C", "CAG", "CAH", "CAT",
    "CI", "CL", "CLX", "CMCSA", "CMI", "COF", "COP", "COST", "CSCO", "CSX",
    "CVS", "CVX", "D", "DE", "DHI", "DHR", "DIS", "DOV", "DTE", "DUK",
    "EA", "ED", "EFX", "EIX", "EL", "EMR", "EOG", "EQR", "ETN", "ETR",
    "EXC", "F", "FDX", "FITB", "GD", "GE", "GILD", "GIS", "GLW", "GPC",
    "GS", "GWW", "HAL", "HAS", "HBAN", "HD", "HES", "HIG", "HON", "HPQ",
    "HRL", "HSY", "HUM", "IBM", "IFF", "INTC", "INTU", "IP", "IPG", "ITW",
    "JBHT", "JCI", "JNJ", "JPM", "K", "KEY", "KLAC", "KMB", "KO", "KR",
    "LEN", "LH", "LLY", "LMT", "LNC", "LOW", "LRCX", "LUV", "MAR", "MAS",
    "MCD", "MCHP", "MCK", "MCO", "MDT", "MET", "MHK", "MKC", "MMC", "MMM",
    "MO", "MRK", "MS", "MSFT", "MSI", "MTB", "MU", "NEE", "NEM", "NI",
    "NKE", "NOC", "NSC", "NTAP", "NTRS", "NUE", "NVDA", "OKE", "OMC", "ORCL",
    "ORLY", "OXY", "PAYX", "PCAR", "PEG", "PEP", "PFE", "PG", "PGR", "PH",
    "PHM", "PNC", "PPG", "PPL", "PRU", "PSA", "PVH", "QCOM", "RF", "RHI",
    "RL", "ROK", "ROP", "ROST", "RTX", "SBUX", "SCHW", "SHW", "SJM", "SLB",
    "SNA", "SO", "SPG", "SRE", "STT", "SWK", "SYK", "SYY", "T", "TAP",
    "TGT", "TJX", "TMO", "TROW", "TRV", "TSN", "TXN", "TXT", "UNH", "UNP",
    "UPS", "USB", "VFC", "VLO", "VMC", "VZ", "WAT", "WBA", "WDC", "WEC",
    "WFC", "WHR", "WM", "WMB", "WMT", "WY", "XEL", "XOM", "YUM", "ZION",
]

MODERN_ADDITIONS = [
    "ABNB", "AMZN", "ANET", "AVGO", "AXON", "BKNG", "CRM", "CRWD", "DDOG",
    "DELL", "GOOGL", "META", "NFLX", "NOW", "PANW", "PLTR", "SHOP", "SNOW",
    "SQ", "TSLA", "TTD", "UBER", "V", "MA", "PYPL", "ZS", "MDB", "NET",
    "SMCI", "MRVL", "ON", "TEAM", "HUBS", "VRT", "COIN", "RBLX",
]

PRESETS = {
    "liquid2004": LIQUID_2004,
    "modern": MODERN_ADDITIONS,
    "all": LIQUID_2004 + MODERN_ADDITIONS,
}


def load_universe(spec: str | None) -> list[str]:
    """Accepts a preset name, a path to a newline/comma list, or tickers."""
    if not spec:
        return list(LIQUID_2004)
    if spec in PRESETS:
        return list(PRESETS[spec])

    path = Path(spec)
    if path.exists():
        raw = path.read_text()
    else:
        raw = spec
    tickers: list[str] = []
    for chunk in raw.replace(",", "\n").splitlines():
        ticker = chunk.strip().upper()
        if ticker and not ticker.startswith("#"):
            tickers.append(ticker)
    if not tickers:
        raise ValueError(f"no tickers found in universe spec {spec!r}")
    # de-dupe, keep order
    return list(dict.fromkeys(tickers))

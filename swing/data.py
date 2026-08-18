"""Market data access.

Single source: the public Yahoo Finance chart endpoint. Daily bars are
split/dividend adjusted so that signals computed today match what the
backtest saw historically; intraday bars are raw (adjustments are
irrelevant within a session).

Everything is cached on disk so a scan or a backtest can be re-run
offline and so we do not hammer the endpoint.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Mozilla/5.0 (compatible; swing-research/1.0)"

DEFAULT_CACHE = Path(".cache")

OHLCV = ["open", "high", "low", "close", "volume"]


class DataError(RuntimeError):
    pass


@dataclass
class FetchStats:
    hits: int = 0
    misses: int = 0
    failures: int = 0


def _http_get(url: str, params: dict, timeout: float, retries: int = 3) -> dict:
    query = urllib.parse.urlencode(params)
    full = f"{url}?{query}"
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(full, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last = exc
            time.sleep(2**attempt)
    raise DataError(f"GET {full} failed after {retries} tries: {last}")


def _parse_chart(payload: dict, symbol: str) -> pd.DataFrame:
    chart = payload.get("chart") or {}
    if chart.get("error"):
        raise DataError(f"{symbol}: {chart['error']}")
    results = chart.get("result") or []
    if not results:
        raise DataError(f"{symbol}: empty chart result")
    res = results[0]
    stamps = res.get("timestamp")
    if not stamps:
        raise DataError(f"{symbol}: no timestamps")

    quote = res["indicators"]["quote"][0]
    frame = pd.DataFrame(
        {
            "open": quote.get("open"),
            "high": quote.get("high"),
            "low": quote.get("low"),
            "close": quote.get("close"),
            "volume": quote.get("volume"),
        },
        index=pd.to_datetime(stamps, unit="s", utc=True),
    )

    adj = (res.get("indicators", {}).get("adjclose") or [{}])[0].get("adjclose")
    if adj is not None:
        frame["adjclose"] = adj

    frame = frame.dropna(subset=["open", "high", "low", "close"])
    frame = frame[~frame.index.duplicated(keep="last")].sort_index()
    if frame.empty:
        raise DataError(f"{symbol}: all bars null")
    return frame


def _apply_adjustment(frame: pd.DataFrame) -> pd.DataFrame:
    """Scale OHLC by adjclose/close so the whole series is comparable.

    Yahoo only adjusts the close. Applying the same factor to open/high/low
    keeps intrabar geometry (gaps, stop distances, ATR) consistent with the
    adjusted close, which is what the strategy trades off.
    """
    out = frame.copy()
    if "adjclose" in out.columns:
        factor = out["adjclose"] / out["close"]
        factor = factor.replace([np.inf, -np.inf], np.nan).ffill().fillna(1.0)
        for col in ("open", "high", "low", "close"):
            out[col] = out[col] * factor
        # Share counts move inversely to price on splits.
        out["volume"] = out["volume"] / factor
        out = out.drop(columns=["adjclose"])
    out["volume"] = out["volume"].fillna(0.0)
    return out[OHLCV]


def _cache_path(cache_dir: Path, symbol: str, interval: str) -> Path:
    safe = symbol.replace("/", "_").replace("^", "_idx_")
    return cache_dir / interval / f"{safe}.csv"


def _read_cache(path: Path, max_age_hours: float | None) -> pd.DataFrame | None:
    if not path.exists():
        return None
    if max_age_hours is not None:
        age = (time.time() - path.stat().st_mtime) / 3600.0
        if age > max_age_hours:
            return None
    try:
        frame = pd.read_csv(path, index_col=0, parse_dates=True)
    except (OSError, ValueError, pd.errors.ParserError):
        return None
    if frame.empty:
        return None
    if frame.index.tz is None:
        frame.index = frame.index.tz_localize("UTC")
    return frame


def get_daily(
    symbol: str,
    *,
    start: str | date | None = None,
    end: str | date | None = None,
    cache_dir: Path | str = DEFAULT_CACHE,
    max_age_hours: float | None = 12.0,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Adjusted daily OHLCV indexed by UTC timestamp, oldest first."""
    cache_dir = Path(cache_dir)
    path = _cache_path(cache_dir, symbol, "1d")

    frame = _read_cache(path, max_age_hours)
    if frame is None:
        payload = _http_get(
            CHART_URL.format(symbol=urllib.parse.quote(symbol)),
            {
                "period1": 0,
                "period2": int(time.time()) + 86400,
                "interval": "1d",
                "events": "div,split",
                "includeAdjustedClose": "true",
            },
            timeout=timeout,
        )
        frame = _apply_adjustment(_parse_chart(payload, symbol))
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path)

    frame = frame[OHLCV].astype(float)
    if start is not None:
        frame = frame[frame.index >= pd.Timestamp(start, tz="UTC")]
    if end is not None:
        frame = frame[frame.index <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
    return frame


def get_intraday(
    symbol: str,
    *,
    interval: str = "5m",
    lookback_days: int = 5,
    cache_dir: Path | str = DEFAULT_CACHE,
    max_age_minutes: float = 5.0,
    timeout: float = 30.0,
) -> pd.DataFrame:
    """Recent intraday bars. Yahoo caps 1m at ~7d and 5m at ~60d."""
    cache_dir = Path(cache_dir)
    path = _cache_path(cache_dir, symbol, interval)
    frame = _read_cache(path, max_age_minutes / 60.0)
    if frame is None:
        payload = _http_get(
            CHART_URL.format(symbol=urllib.parse.quote(symbol)),
            {"range": f"{lookback_days}d", "interval": interval},
            timeout=timeout,
        )
        frame = _parse_chart(payload, symbol)
        frame = frame[OHLCV] if "adjclose" not in frame else frame[OHLCV]
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_csv(path)
    return frame[OHLCV].astype(float)


def last_quote(symbol: str, *, cache_dir: Path | str = DEFAULT_CACHE, timeout: float = 30.0) -> dict:
    """Latest price snapshot, including pre/post market when available."""
    payload = _http_get(
        CHART_URL.format(symbol=urllib.parse.quote(symbol)),
        {"range": "1d", "interval": "1m", "includePrePost": "true"},
        timeout=timeout,
    )
    meta = payload["chart"]["result"][0]["meta"]
    stamp = meta.get("regularMarketTime")
    return {
        "symbol": symbol,
        "price": meta.get("regularMarketPrice"),
        "previous_close": meta.get("chartPreviousClose") or meta.get("previousClose"),
        "currency": meta.get("currency"),
        "exchange": meta.get("fullExchangeName"),
        "as_of": datetime.fromtimestamp(stamp, tz=timezone.utc).isoformat() if stamp else None,
    }


def load_many(
    symbols: list[str],
    *,
    start: str | date | None = None,
    end: str | date | None = None,
    cache_dir: Path | str = DEFAULT_CACHE,
    max_age_hours: float | None = 12.0,
    min_bars: int = 250,
    verbose: bool = False,
) -> tuple[dict[str, pd.DataFrame], FetchStats]:
    """Fetch a universe, skipping symbols that fail or are too short."""
    out: dict[str, pd.DataFrame] = {}
    stats = FetchStats()
    for symbol in symbols:
        try:
            frame = get_daily(
                symbol, start=start, end=end, cache_dir=cache_dir, max_age_hours=max_age_hours
            )
        except DataError as exc:
            stats.failures += 1
            if verbose:
                print(f"  skip {symbol}: {exc}")
            continue
        if len(frame) < min_bars:
            stats.failures += 1
            if verbose:
                print(f"  skip {symbol}: only {len(frame)} bars")
            continue
        out[symbol] = frame
        stats.hits += 1
    return out, stats

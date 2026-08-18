"""Does the entry actually have an edge?

A backtest answers "would this have made money", which on a rising market
is mostly a question about beta. This module answers the sharper question:
after a signal, does the stock beat what you would have got anyway?

Two reference points are reported, and the second is the one that matters:

* vs the benchmark -- the signal's forward return minus SPY's over the
  same window.
* vs the *control* -- the same number computed over every liquid name in
  the universe that was above its 200-day MA in a risk-on market. That is
  the pool the strategy draws from, so beating SPY while merely matching
  the control means the signal added nothing; it just held equities.

Forward returns are measured from the NEXT bar's open, because that is
where the strategy actually fills.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StrategyParams
from .indicators import dollar_volume, sma
from .strategy import compute_regime

DEFAULT_HORIZONS = (3, 5, 10, 20)


@dataclass
class EdgeReport:
    table: pd.DataFrame
    signals: int
    control_signals: int

    def __str__(self) -> str:
        return self.table.to_string()


def _forward_returns(
    frame: pd.DataFrame, mask: np.ndarray, horizons: tuple[int, ...]
) -> list[tuple]:
    opens = frame["open"].to_numpy()
    closes = frame["close"].to_numpy()
    index = frame.index
    n = len(frame)
    rows = []
    for i in np.flatnonzero(mask):
        if i + 1 >= n:
            continue
        entry = opens[i + 1]
        if not np.isfinite(entry) or entry <= 0:
            continue
        rows.append(
            (index[i],) + tuple(closes[min(i + 1 + h, n - 1)] / entry - 1.0 for h in horizons)
        )
    return rows


def _benchmark_forward(benchmark: pd.DataFrame, horizons: tuple[int, ...]) -> pd.DataFrame:
    opens = benchmark["open"].to_numpy()
    closes = benchmark["close"].to_numpy()
    n = len(benchmark)
    data = {}
    for h in horizons:
        values = np.full(n, np.nan)
        for i in range(n - 1):
            values[i] = closes[min(i + 1 + h, n - 1)] / opens[i + 1] - 1.0
        data[h] = values
    return pd.DataFrame(data, index=benchmark.index)


def _control_mask(feat: pd.DataFrame, params: StrategyParams, regime: pd.Series) -> np.ndarray:
    """Every liquid name in an uptrend on a risk-on day -- the honest baseline."""
    aligned = regime.reindex(feat.index).ffill().fillna(False)
    mask = (
        (feat["close"] >= params.min_price)
        & (feat["dollar_volume"] >= params.min_dollar_volume)
        & (feat["close"] > feat["sma_slow"])
        & aligned
    )
    return mask.fillna(False).to_numpy()


def _stats(frame: pd.DataFrame, bench_fwd: pd.DataFrame, horizons) -> dict:
    out = {}
    for h in horizons:
        raw = frame[f"r{h}"]
        bench = frame["date"].map(bench_fwd[h])
        excess = raw - bench
        by_date = excess.groupby(frame["date"]).mean()
        tstat = (
            by_date.mean() / (by_date.std() / np.sqrt(len(by_date)))
            if len(by_date) > 2 and by_date.std() > 0
            else np.nan
        )
        out[h] = {
            "n": int(len(raw)),
            "mean_return": float(raw.mean()),
            "median_return": float(raw.median()),
            "hit_rate": float((raw > 0).mean()),
            "excess_vs_benchmark": float(excess.mean()),
            "t_stat": float(tstat) if np.isfinite(tstat) else np.nan,
        }
    return out


def signal_edge(
    prepared: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    params: StrategyParams,
    *,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    start: str | None = None,
) -> EdgeReport:
    """Forward-return study of the prepared universe's signals vs its control."""
    regime = compute_regime(benchmark, params)
    bench_fwd = _benchmark_forward(benchmark, horizons)

    signal_rows: list[tuple] = []
    control_rows: list[tuple] = []
    for feat in prepared.values():
        window = feat.loc[start:] if start else feat
        if window.empty:
            continue
        mask = window["signal"].fillna(False).to_numpy()
        signal_rows.extend(_forward_returns(window, mask, horizons))
        control_rows.extend(
            _forward_returns(window, _control_mask(window, params, regime), horizons)
        )

    columns = ["date"] + [f"r{h}" for h in horizons]
    signals = pd.DataFrame(signal_rows, columns=columns)
    control = pd.DataFrame(control_rows, columns=columns)
    if signals.empty:
        raise ValueError("no signals in the requested window")

    signal_stats = _stats(signals, bench_fwd, horizons)
    control_stats = _stats(control, bench_fwd, horizons) if not control.empty else {}

    rows = []
    for h in horizons:
        row = {
            "horizon_sessions": h,
            "signals": signal_stats[h]["n"],
            "mean_return": round(signal_stats[h]["mean_return"], 5),
            "hit_rate": round(signal_stats[h]["hit_rate"], 4),
            "excess_vs_spy": round(signal_stats[h]["excess_vs_benchmark"], 5),
            "t_stat": round(signal_stats[h]["t_stat"], 2),
        }
        if control_stats:
            row["control_mean_return"] = round(control_stats[h]["mean_return"], 5)
            row["edge_vs_control"] = round(
                signal_stats[h]["mean_return"] - control_stats[h]["mean_return"], 5
            )
        rows.append(row)

    return EdgeReport(
        table=pd.DataFrame(rows).set_index("horizon_sessions"),
        signals=len(signals),
        control_signals=len(control),
    )

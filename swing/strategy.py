"""The swing setup.

One idea, four gates, in this order:

  regime   -- the broad market is in an uptrend, otherwise sit in cash
  trend    -- the name itself is in an established uptrend
  weakness -- it has just pulled back / cooled off inside that uptrend
  risk     -- the protective stop is close enough to survive being all-in

Two entry triggers implement the "weakness" gate:

  "oversold" (default) buys a 2-period RSI washout inside a strong uptrend
      and sells when RSI(2) recovers. Measured against a like-for-like
      control -- every liquid name above its 200-day MA in a risk-on
      market -- this is the variant that carried a real excess return.

  "reclaim" buys the first close above the prior day's high after a dip.
      It is the textbook pullback entry and it is kept here so the
      comparison can be reproduced; on this universe it did not beat the
      control. See README.

A bar that passes every gate is a *signal*, and the backtest acts on it at
the NEXT bar's open -- never on the same close.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import StrategyParams
from .indicators import compute_features, rolling_return, sma

ENTRY_MODES = ("oversold", "reclaim")


@dataclass(frozen=True)
class Candidate:
    """A triggered setup, as of the close of `asof`."""

    symbol: str
    asof: pd.Timestamp
    close: float
    stop: float
    stop_pct: float
    score: float
    atr: float
    rsi: float
    rsi_fast: float
    adx: float
    mom_long: float
    target: float | None

    def as_dict(self) -> dict:
        data = {
            "symbol": self.symbol,
            "asof": self.asof.date().isoformat(),
            "close": round(self.close, 4),
            "stop": round(self.stop, 4),
            "stop_pct": round(self.stop_pct, 4),
            "risk_per_share": round(self.close - self.stop, 4),
            "score": round(self.score, 4),
            "atr": round(self.atr, 4),
            "rsi": round(self.rsi, 2),
            "rsi_fast": round(self.rsi_fast, 2),
            "adx": round(self.adx, 2),
            "momentum_6m": round(self.mom_long, 4),
        }
        if self.target is not None:
            data["target"] = round(self.target, 4)
        return data


def compute_regime(benchmark: pd.DataFrame, params: StrategyParams) -> pd.Series:
    """True on bars where the benchmark closed above its long moving average."""
    ma = sma(benchmark["close"], params.regime_ma)
    return (benchmark["close"] > ma).where(ma.notna(), False).rename("regime_ok")


def benchmark_momentum(benchmark: pd.DataFrame, params: StrategyParams) -> pd.Series:
    return rolling_return(benchmark["close"], params.momentum_lookback).rename("bench_mom")


def _score(features: pd.DataFrame, params: StrategyParams) -> pd.Series:
    """Self-contained 0-ish..1-ish quality score, comparable across symbols.

    Deliberately not a cross-sectional rank: a live scan must be able to
    score one symbol in isolation and get the same number the backtest used.

    Which candidate you pick on a busy day turned out to matter much less
    than whether you take the trade at all -- every ranking rule tested
    landed inside the noise of picking at random. The weights below are a
    defensible prior (trend quality and a tight stop), not a fitted edge.
    """
    momentum = features["mom_long"].clip(-0.5, 1.5) / 1.5
    tightness = 1.0 - (features["stop_pct"] / params.max_stop_pct).clip(0.0, 1.0)
    trend = (features["adx"] / 50.0).clip(0.0, 1.0)
    return (
        params.weight_momentum * momentum
        + params.weight_tightness * tightness
        + params.weight_trend * trend
    )


def prepare(
    frame: pd.DataFrame,
    params: StrategyParams,
    bench_mom: pd.Series | None = None,
) -> pd.DataFrame:
    """Turn raw bars into per-bar features, stop levels and a signal flag."""
    feat = compute_features(frame, params)

    # --- risk: stop below the pullback low, or a fixed ATR distance ---
    pivot_low = pd.concat(
        [feat["swing_low"], feat["low"]], axis=1
    ).min(axis=1) - 0.10 * feat["atr"]
    atr_stop = feat["close"] - params.stop_atr_mult * feat["atr"]
    feat["stop"] = pd.concat([pivot_low, atr_stop], axis=1).min(axis=1)
    feat["stop_pct"] = (feat["close"] - feat["stop"]) / feat["close"]

    # --- gate 2: tradable and trending ---
    tradable = (
        (feat["close"] >= params.min_price)
        & (feat["dollar_volume"] >= params.min_dollar_volume)
        & feat["atr_pct"].between(params.min_atr_pct, params.max_atr_pct)
    )
    trending = (
        (feat["close"] > feat["sma_slow"])
        & (feat["sma_mid"] > feat["sma_slow"])
        & (feat["sma_mid_slope"] > 0)
        & (feat["adx"] >= params.min_adx)
        & (feat["mom_long"] >= params.min_momentum)
    )
    if params.require_relative_strength and bench_mom is not None:
        aligned = bench_mom.reindex(feat.index).ffill()
        trending &= feat["mom_long"] > aligned

    # --- gate 3: the entry trigger ---
    if params.entry_mode not in ENTRY_MODES:
        raise ValueError(f"entry_mode must be one of {ENTRY_MODES}, got {params.entry_mode!r}")

    if params.entry_mode == "oversold":
        trigger = feat["rsi_fast"] < params.oversold_rsi
        exit_signal = feat["rsi_fast"] > params.exit_rsi
    else:
        dip = (
            (feat["rsi"] < params.pullback_rsi)
            | (feat["pullback_atr"] >= params.min_pullback_atr)
            | (feat["low"] <= feat["sma_fast"])
        )
        dipped_recently = (
            dip.shift(1).fillna(False)
            .rolling(params.trigger_window, min_periods=1).max().astype(bool)
        )
        trigger = (
            dipped_recently
            & (feat["close"] > feat["prior_high"])
            & (feat["close"] > feat["sma_fast"])
            & (feat["ext_atr"] <= params.max_extension_atr)
        )
        exit_signal = pd.Series(False, index=feat.index)

    if params.exit_below_ma:
        exit_signal = exit_signal | (feat["close"] < feat[params.exit_below_ma])
    feat["exit_signal"] = exit_signal.fillna(False)

    # --- gate 4: the stop is near enough that one loss cannot end the account ---
    risk_ok = (feat["stop"] < feat["close"]) & (feat["stop_pct"] <= params.max_stop_pct)

    feat["signal"] = (tradable & trending & trigger & risk_ok).fillna(False)
    feat["score"] = _score(feat, params).where(feat["signal"], np.nan)
    return feat


def target_price(entry: float, stop: float, params: StrategyParams) -> float | None:
    if params.target_r <= 0:
        return None
    return entry + params.target_r * (entry - stop)


class SignalBook:
    """Every signal in a prepared universe, bucketed by date.

    The backtest asks "what fired on this date?" once per session. Doing
    that with a per-symbol lookup is O(days x symbols); signals are sparse,
    so bucketing them up front turns the same question into a dict hit.
    """

    __slots__ = ("_by_date", "params")

    _FIELDS = ("close", "stop", "stop_pct", "score", "atr", "rsi", "rsi_fast", "adx", "mom_long")

    def __init__(self, prepared: dict[str, pd.DataFrame], params: StrategyParams):
        self.params = params
        by_date: dict[pd.Timestamp, list[Candidate]] = {}
        for symbol, feat in prepared.items():
            fired = feat.loc[feat["signal"].fillna(False).astype(bool), list(self._FIELDS)]
            for row in fired.itertuples():
                values = dict(zip(self._FIELDS, row[1:]))
                candidate = Candidate(
                    symbol=symbol,
                    asof=row.Index,
                    target=target_price(values["close"], values["stop"], params),
                    **values,
                )
                by_date.setdefault(row.Index, []).append(candidate)
        for bucket in by_date.values():
            bucket.sort(key=lambda c: (-c.score, c.symbol))
        self._by_date = by_date

    def on(self, asof: pd.Timestamp) -> list[Candidate]:
        return self._by_date.get(asof, ())

    def best(self, asof: pd.Timestamp) -> Candidate | None:
        bucket = self._by_date.get(asof)
        return bucket[0] if bucket else None

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_date.values())


def candidates_on(
    prepared: dict[str, pd.DataFrame],
    asof: pd.Timestamp,
    params: StrategyParams,
) -> list[Candidate]:
    """Every symbol whose bar at `asof` fired, best score first."""
    found: list[Candidate] = []
    for symbol, feat in prepared.items():
        if asof not in feat.index:
            continue
        row = feat.loc[asof]
        if not bool(row["signal"]):
            continue
        found.append(
            Candidate(
                symbol=symbol,
                asof=asof,
                close=float(row["close"]),
                stop=float(row["stop"]),
                stop_pct=float(row["stop_pct"]),
                score=float(row["score"]),
                atr=float(row["atr"]),
                rsi=float(row["rsi"]),
                rsi_fast=float(row["rsi_fast"]),
                adx=float(row["adx"]),
                mom_long=float(row["mom_long"]),
                target=target_price(float(row["close"]), float(row["stop"]), params),
            )
        )
    # Ties broken by symbol so a run is reproducible.
    found.sort(key=lambda c: (-c.score, c.symbol))
    return found

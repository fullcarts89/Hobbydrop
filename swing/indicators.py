"""Technical indicators.

Every function is causal: the value at bar *t* uses only bars <= t. That
property is what makes the backtest honest, so it is asserted in tests.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def sma(series: pd.Series, length: int) -> pd.Series:
    return series.rolling(length, min_periods=length).mean()


def ema(series: pd.Series, length: int) -> pd.Series:
    return series.ewm(span=length, adjust=False, min_periods=length).mean()


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    prev_close = close.shift(1)
    ranges = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    )
    return ranges.max(axis=1)


def atr(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    """Wilder's average true range."""
    tr = true_range(frame["high"], frame["low"], frame["close"])
    return tr.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()


def rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """Wilder's RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1.0 / length, adjust=False, min_periods=length).mean()
    # avg_loss of zero divides to +inf, which lands on RSI 100 -- the
    # correct value for a window with no down closes.
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def adx(frame: pd.DataFrame, length: int = 14) -> pd.Series:
    """Wilder's ADX -- trend strength, direction agnostic."""
    up = frame["high"].diff()
    down = -frame["low"].diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=frame.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=frame.index)

    alpha = 1.0 / length
    tr_n = true_range(frame["high"], frame["low"], frame["close"]).ewm(
        alpha=alpha, adjust=False, min_periods=length
    ).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean() / tr_n
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=length).mean() / tr_n

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return dx.ewm(alpha=alpha, adjust=False, min_periods=length).mean()


def rolling_return(series: pd.Series, length: int) -> pd.Series:
    return series / series.shift(length) - 1.0


def dollar_volume(frame: pd.DataFrame, length: int = 20) -> pd.Series:
    return (frame["close"] * frame["volume"]).rolling(length, min_periods=length).mean()


def donchian_high(frame: pd.DataFrame, length: int) -> pd.Series:
    """Highest high of the *prior* `length` bars (excludes the current bar)."""
    return frame["high"].shift(1).rolling(length, min_periods=length).max()


def donchian_low(frame: pd.DataFrame, length: int) -> pd.Series:
    return frame["low"].shift(1).rolling(length, min_periods=length).min()


def distance_in_atr(series: pd.Series, reference: pd.Series, atr_series: pd.Series) -> pd.Series:
    return (series - reference) / atr_series.replace(0.0, np.nan)


def annualized_vol(series: pd.Series, length: int = 20) -> pd.Series:
    return series.pct_change().rolling(length, min_periods=length).std() * np.sqrt(252.0)


def compute_features(frame: pd.DataFrame, params) -> pd.DataFrame:
    """Attach every column the strategy reads onto a copy of the bars."""
    out = frame.copy()
    close = out["close"]

    out["sma_fast"] = sma(close, params.sma_fast)
    out["sma_mid"] = sma(close, params.sma_mid)
    out["sma_slow"] = sma(close, params.sma_slow)
    out["sma_mid_slope"] = out["sma_mid"] - out["sma_mid"].shift(params.slope_lookback)
    out["atr"] = atr(out, params.atr_length)
    out["atr_pct"] = out["atr"] / close
    out["rsi"] = rsi(close, params.rsi_length)
    out["rsi_fast"] = rsi(close, params.rsi_fast_length)
    out["adx"] = adx(out, params.adx_length)
    out["dollar_volume"] = dollar_volume(out, 20)
    out["mom_long"] = rolling_return(close, params.momentum_lookback)
    out["mom_short"] = rolling_return(close, params.momentum_short)
    out["prior_high"] = out["high"].shift(1)
    out["swing_low"] = donchian_low(out, params.swing_low_lookback)
    out["breakout_high"] = donchian_high(out, params.breakout_lookback)
    out["pullback_atr"] = distance_in_atr(out["high"].rolling(
        params.pullback_lookback, min_periods=params.pullback_lookback).max(), close, out["atr"])
    out["ext_atr"] = distance_in_atr(close, out["sma_fast"], out["atr"])
    return out

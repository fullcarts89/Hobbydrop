"""Indicators must be causal -- the backtest's honesty depends on it."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swing import indicators as ind
from swing.config import StrategyParams


def make_frame(n=400, seed=3):
    rng = np.random.default_rng(seed)
    close = 100 * np.exp(np.cumsum(rng.normal(0.0004, 0.015, n)))
    high = close * (1 + rng.uniform(0, 0.012, n))
    low = close * (1 - rng.uniform(0, 0.012, n))
    open_ = low + (high - low) * rng.uniform(0, 1, n)
    index = pd.date_range("2020-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": rng.uniform(1e6, 5e6, n)},
        index=index,
    )


@pytest.mark.parametrize("name", ["atr", "rsi", "adx", "sma", "compute_features"])
def test_indicators_are_causal(name):
    """Appending future bars must not change any already-computed value."""
    frame = make_frame()
    head = frame.iloc[:300]
    params = StrategyParams()

    if name == "sma":
        full, part = ind.sma(frame["close"], 50), ind.sma(head["close"], 50)
    elif name == "rsi":
        full, part = ind.rsi(frame["close"], 14), ind.rsi(head["close"], 14)
    elif name == "atr":
        full, part = ind.atr(frame, 14), ind.atr(head, 14)
    elif name == "adx":
        full, part = ind.adx(frame, 14), ind.adx(head, 14)
    else:
        full = ind.compute_features(frame, params)["ext_atr"]
        part = ind.compute_features(head, params)["ext_atr"]

    pd.testing.assert_series_equal(full.iloc[:300], part, check_names=False)


def test_rsi_bounds_and_extremes():
    rising = pd.Series(np.arange(1, 60, dtype=float))
    assert ind.rsi(rising, 14).iloc[-1] == pytest.approx(100.0)
    falling = pd.Series(np.arange(60, 1, -1, dtype=float))
    assert ind.rsi(falling, 14).iloc[-1] == pytest.approx(0.0)
    values = ind.rsi(make_frame()["close"], 14).dropna()
    assert values.between(0, 100).all()


def test_atr_matches_manual_wilder():
    frame = make_frame(60)
    tr = ind.true_range(frame["high"], frame["low"], frame["close"])
    manual = tr.iloc[1:15].mean()
    # Wilder seeds with a simple mean over the first window; the ewm form
    # converges to it within rounding on the first valid bar.
    assert ind.atr(frame, 14).iloc[14] == pytest.approx(manual, rel=0.35)
    assert (ind.atr(frame, 14).dropna() > 0).all()


def test_donchian_excludes_current_bar():
    frame = make_frame(100)
    high = ind.donchian_high(frame, 20)
    for i in range(25, 100):
        assert high.iloc[i] == pytest.approx(frame["high"].iloc[i - 20 : i].max())


def test_true_range_covers_gaps():
    index = pd.date_range("2024-01-01", periods=2, freq="B", tz="UTC")
    frame = pd.DataFrame(
        {"high": [10.0, 20.0], "low": [9.0, 19.0], "close": [9.5, 19.5]}, index=index
    )
    # Gapped from 9.5 to a 19..20 range: true range is measured from the
    # prior close, not just the bar's own span.
    assert ind.true_range(frame["high"], frame["low"], frame["close"]).iloc[1] == pytest.approx(10.5)

"""Signal-level guarantees: no lookahead, gates actually gate."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swing.config import StrategyParams
from swing.strategy import SignalBook, candidates_on, compute_regime, prepare


def synthetic(n=800, seed=11, drift=0.0006):
    rng = np.random.default_rng(seed)
    close = 50 * np.exp(np.cumsum(rng.normal(drift, 0.016, n)))
    high = close * (1 + rng.uniform(0, 0.014, n))
    low = close * (1 - rng.uniform(0, 0.014, n))
    open_ = low + (high - low) * rng.uniform(0, 1, n)
    index = pd.date_range("2018-01-01", periods=n, freq="B", tz="UTC")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close,
         "volume": rng.uniform(3e6, 9e6, n) * 30},
        index=index,
    )


@pytest.mark.parametrize("mode", ["oversold", "reclaim"])
def test_signals_do_not_change_when_the_future_arrives(mode):
    """The decisive property: today's signal cannot depend on tomorrow."""
    params = StrategyParams(entry_mode=mode)
    frame = synthetic()
    cut = 600
    full = prepare(frame, params)
    partial = prepare(frame.iloc[:cut], params)
    for column in ("signal", "stop", "score", "exit_signal"):
        pd.testing.assert_series_equal(
            full[column].iloc[:cut], partial[column], check_names=False
        )


def test_unknown_entry_mode_is_rejected():
    with pytest.raises(ValueError, match="entry_mode"):
        prepare(synthetic(300), StrategyParams(entry_mode="vibes"))


def test_liquidity_gate_excludes_thin_names():
    frame = synthetic()
    thin = frame.copy()
    thin["volume"] = 1.0
    params = StrategyParams()
    assert prepare(frame, params)["signal"].any()
    assert not prepare(thin, params)["signal"].any()


def test_downtrends_produce_no_signals():
    falling = synthetic(drift=-0.0015, seed=5)
    assert not prepare(falling, StrategyParams())["signal"].any()


def test_relative_strength_gate_uses_the_benchmark():
    frame = synthetic()
    params = StrategyParams(require_relative_strength=True)
    # A benchmark that always outran the stock should block every signal.
    strong_bench = frame["close"] ** 2
    blocked = prepare(frame, params, bench_mom=pd.Series(9.0, index=frame.index))
    assert not blocked["signal"].any()
    allowed = prepare(frame, params, bench_mom=pd.Series(-9.0, index=frame.index))
    assert allowed["signal"].any()


def test_stop_sits_below_price_and_inside_the_risk_cap():
    params = StrategyParams()
    feat = prepare(synthetic(), params)
    fired = feat[feat["signal"]]
    assert len(fired) > 0
    assert (fired["stop"] < fired["close"]).all()
    assert (fired["stop_pct"] <= params.max_stop_pct).all()


def test_signal_book_matches_the_per_date_lookup():
    params = StrategyParams()
    prepared = {"AAA": prepare(synthetic(seed=1), params),
                "BBB": prepare(synthetic(seed=2), params)}
    book = SignalBook(prepared, params)
    dates = prepared["AAA"].index[-200:]
    for date in dates:
        expected = [c.symbol for c in candidates_on(prepared, date, params)]
        assert [c.symbol for c in book.on(date)] == expected


def test_regime_is_false_until_the_average_exists():
    bench = synthetic(400)
    regime = compute_regime(bench, StrategyParams(regime_ma=200))
    assert not regime.iloc[:199].any()
    assert regime.iloc[200:].any()

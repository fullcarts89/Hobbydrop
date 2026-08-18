"""Engine mechanics, on hand-built bars where the right answer is known."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from swing.backtest import run_backtest
from swing.config import ExecutionConfig, RunConfig, StrategyParams

FIELDS = ["close", "stop", "stop_pct", "score", "atr", "rsi", "rsi_fast", "adx", "mom_long"]


def bars(rows, signals=None, exits=None, stops=None):
    """rows: list of (open, high, low, close)."""
    index = pd.date_range("2024-01-02", periods=len(rows), freq="B", tz="UTC")
    frame = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=index)
    frame["volume"] = 1e7
    frame["atr"] = 1.0
    frame["rsi"] = 50.0
    frame["rsi_fast"] = 50.0
    frame["adx"] = 25.0
    frame["mom_long"] = 0.3
    frame["signal"] = False
    frame["exit_signal"] = False
    frame["score"] = np.nan
    frame["stop"] = frame["close"] - 5.0
    frame["stop_pct"] = 5.0 / frame["close"]
    for i in signals or []:
        frame.iloc[i, frame.columns.get_loc("signal")] = True
        frame.iloc[i, frame.columns.get_loc("score")] = 1.0
    for i in exits or []:
        frame.iloc[i, frame.columns.get_loc("exit_signal")] = True
    for i, value in (stops or {}).items():
        frame.iloc[i, frame.columns.get_loc("stop")] = value
    return frame


def benchmark_for(frame, above_ma=True):
    """SPY bars engineered so the regime filter is on (or off) throughout."""
    n = len(frame)
    level = np.full(n, 100.0)
    if above_ma:
        level = np.linspace(50.0, 200.0, n)
    bench = pd.DataFrame(
        {"open": level, "high": level, "low": level, "close": level, "volume": 1e9},
        index=frame.index,
    )
    return bench


def config(**exec_kwargs):
    execution = ExecutionConfig(
        **{"starting_cash": 10_000.0, "slippage_bps": 0.0, "reserve_pct": 0.0, **exec_kwargs}
    )
    # regime_ma small enough that the synthetic benchmark warms up fast
    return RunConfig(params=StrategyParams(regime_ma=3, max_hold_bars=50), execution=execution)


def run(frame, *, exec_kwargs=None, above_ma=True):
    bench = benchmark_for(frame, above_ma)
    return run_backtest({"TEST": frame}, bench, config(**(exec_kwargs or {})))


def test_entry_fills_at_next_open_never_the_signal_close():
    frame = bars(
        [(10, 10, 10, 10)] * 5 + [(10, 12, 10, 12), (20, 21, 19, 20), (20, 21, 19, 20)],
        signals=[5],
    )
    result = run(frame)
    assert len(result.trades) + (1 if result.open_position else 0) == 1
    position = result.open_position
    # signal closed at 12; the fill is the *next* bar's open of 20
    assert position["entry_price"] == pytest.approx(20.0)
    assert position["entry_date"] == frame.index[6].date().isoformat()


def test_gap_through_the_stop_fills_at_the_open():
    frame = bars(
        [(10, 10, 10, 10)] * 5
        + [(10, 10, 10, 10),      # signal bar
           (10, 11, 9, 10),       # entry at 10, stop 5
           (4, 4.5, 3, 3.5)],     # gaps to 4, straight through the 5 stop
        signals=[5],
        stops={5: 5.0},
    )
    result = run(frame)
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    # filled at the gapped open, not at the unreachable stop price
    assert trade.exit_price == pytest.approx(4.0)


def test_stop_is_assumed_to_hit_before_the_target_in_the_same_bar():
    params = StrategyParams(regime_ma=3, target_r=2.0, max_hold_bars=50)
    frame = bars(
        [(10, 10, 10, 10)] * 5
        + [(10, 10, 10, 10), (10, 11, 9, 10), (10, 30, 4, 25)],
        signals=[5],
        stops={5: 5.0},
    )
    execution = ExecutionConfig(starting_cash=10_000.0, slippage_bps=0.0, reserve_pct=0.0)
    result = run_backtest(
        {"TEST": frame}, benchmark_for(frame), RunConfig(params=params, execution=execution)
    )
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_price == pytest.approx(5.0)


def test_all_in_whole_shares_and_cash_never_goes_negative():
    frame = bars(
        [(10, 10, 10, 10)] * 5 + [(10, 10, 10, 10), (33, 34, 32, 33), (33, 34, 32, 33)],
        signals=[5],
    )
    result = run(frame)
    position = result.open_position
    assert position["shares"] == 10_000 // 33
    assert (result.equity > 0).all()
    # leftover cash is smaller than one more share
    leftover = 10_000 - position["shares"] * 33
    assert 0 <= leftover < 33


def test_only_one_position_at_a_time():
    frame_a = bars([(10, 10, 10, 10)] * 12, signals=[3, 5, 7])
    frame_b = bars([(20, 20, 20, 20)] * 12, signals=[3, 5, 7])
    frame_b["score"] = frame_b["score"].where(frame_b["score"].isna(), 0.5)
    bench = benchmark_for(frame_a)
    result = run_backtest({"AAA": frame_a, "BBB": frame_b}, bench, config())
    # never more than one open trade: closed trades must not overlap in time
    spans = [(t.entry_date, t.exit_date) for t in result.trades if t.exit_date]
    for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
        assert e1 <= s2


def test_higher_score_wins_the_slot():
    frame_a = bars([(10, 10, 10, 10)] * 10, signals=[5])
    frame_b = bars([(20, 20, 20, 20)] * 10, signals=[5])
    frame_a.loc[frame_a.index[5], "score"] = 0.2
    frame_b.loc[frame_b.index[5], "score"] = 0.9
    result = run_backtest({"AAA": frame_a, "BBB": frame_b}, benchmark_for(frame_a), config())
    assert result.open_position["symbol"] == "BBB"


def test_no_entries_while_the_regime_is_risk_off():
    frame = bars([(10, 10, 10, 10)] * 10, signals=[5])
    result = run(frame, above_ma=False)
    assert result.trades == []
    assert result.open_position is None
    assert result.pending_order is None


def test_equity_reconciles_with_realised_pnl():
    frame = bars(
        [(10, 10, 10, 10)] * 5
        + [(10, 10, 10, 10), (10, 11, 9, 10), (12, 13, 11, 12), (12, 13, 11, 12)],
        signals=[5],
        exits=[7],
    )
    result = run(frame)
    trade = result.trades[0]
    assert trade.exit_reason == "signal_exit"
    assert float(result.equity.iloc[-1]) == pytest.approx(10_000.0 + trade.pnl)


def test_slippage_moves_both_fills_against_you():
    rows = [(10, 10, 10, 10)] * 5 + [(10, 10, 10, 10), (10, 11, 9, 10), (10, 11, 9, 10),
                                     (10, 11, 9, 10)]
    clean = run(bars(rows, signals=[5], exits=[7]))
    slipped = run(bars(rows, signals=[5], exits=[7]), exec_kwargs={"slippage_bps": 50.0})
    assert slipped.trades[0].entry_price > clean.trades[0].entry_price
    assert slipped.trades[0].exit_price < clean.trades[0].exit_price


def test_time_stop_closes_a_stale_trade():
    params = StrategyParams(regime_ma=3, max_hold_bars=3)
    frame = bars([(10, 10, 10, 10)] * 20, signals=[5])
    execution = ExecutionConfig(starting_cash=10_000.0, slippage_bps=0.0, reserve_pct=0.0)
    result = run_backtest(
        {"TEST": frame}, benchmark_for(frame), RunConfig(params=params, execution=execution)
    )
    assert result.trades[0].exit_reason == "time_stop"
    assert result.trades[0].bars_held == 3

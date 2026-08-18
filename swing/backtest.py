"""All-in, one-position-at-a-time backtest engine.

Rules of the simulation, chosen so the result is believable rather than
flattering:

* A signal is generated from bar *t*'s close and filled at bar *t+1*'s
  open. Nothing is ever filled at a price the strategy could not have
  known was available.
* The whole account goes into one name -- no margin, no options, no
  second position -- which is exactly the constraint being tested.
* Stops are checked against the bar's low, and a gap through the stop
  fills at the open, not at the stop.
* If a bar touches both the stop and the target, the stop is assumed to
  have hit first.
* Slippage is charged on both sides; idle cash earns whatever
  `cash_yield_annual` says, which is zero by default.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field

import numpy as np
import pandas as pd

from .config import ExecutionConfig, RunConfig, StrategyParams
from .strategy import SignalBook, compute_regime, benchmark_momentum, prepare, target_price

TRADING_DAYS = 252


@dataclass
class Trade:
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: int
    initial_stop: float
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    bars_held: int = 0
    mae_pct: float = 0.0            # worst close-to-date drawdown inside the trade
    mfe_pct: float = 0.0            # best excursion inside the trade
    commission: float = 0.0

    @property
    def risk_per_share(self) -> float:
        return self.entry_price - self.initial_stop

    @property
    def pnl(self) -> float:
        if self.exit_price is None:
            return 0.0
        return (self.exit_price - self.entry_price) * self.shares - self.commission

    @property
    def return_pct(self) -> float:
        if self.exit_price is None:
            return 0.0
        return self.exit_price / self.entry_price - 1.0

    @property
    def r_multiple(self) -> float:
        if self.exit_price is None or self.risk_per_share <= 0:
            return 0.0
        return (self.exit_price - self.entry_price) / self.risk_per_share

    def to_row(self) -> dict:
        return {
            "symbol": self.symbol,
            "entry_date": self.entry_date.date().isoformat(),
            "entry_price": round(self.entry_price, 4),
            "exit_date": self.exit_date.date().isoformat() if self.exit_date is not None else None,
            "exit_price": round(self.exit_price, 4) if self.exit_price is not None else None,
            "shares": self.shares,
            "initial_stop": round(self.initial_stop, 4),
            "exit_reason": self.exit_reason,
            "bars_held": self.bars_held,
            "pnl": round(self.pnl, 2),
            "return_pct": round(self.return_pct, 4),
            "r_multiple": round(self.r_multiple, 3),
            "mae_pct": round(self.mae_pct, 4),
            "mfe_pct": round(self.mfe_pct, 4),
        }


@dataclass
class _Position:
    trade: Trade
    stop: float
    target: float | None
    highest: float
    pending_exit: str = ""


@dataclass
class BacktestResult:
    equity: pd.Series
    trades: list[Trade]
    benchmark: pd.Series | None
    stats: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    open_position: dict | None = None
    pending_order: dict | None = None

    def blotter(self) -> pd.DataFrame:
        return pd.DataFrame([t.to_row() for t in self.trades])


def _buy_price(raw: float, execution: ExecutionConfig) -> float:
    return raw * (1.0 + execution.slippage_bps / 10_000.0)


def _sell_price(raw: float, execution: ExecutionConfig) -> float:
    return raw * (1.0 - execution.slippage_bps / 10_000.0)


def run_backtest(
    prepared: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    config: RunConfig,
    *,
    start: pd.Timestamp | None = None,
    end: pd.Timestamp | None = None,
    book: SignalBook | None = None,
) -> BacktestResult:
    params, execution = config.params, config.execution
    book = book if book is not None else SignalBook(prepared, params)
    regime = compute_regime(benchmark, params)

    calendar = benchmark.index
    if start is not None:
        calendar = calendar[calendar >= start]
    if end is not None:
        calendar = calendar[calendar <= end]
    if len(calendar) < 2:
        raise ValueError("not enough bars in the requested window")

    cash = float(execution.starting_cash)
    position: _Position | None = None
    pending_entry: tuple[str, float, float | None] | None = None
    trades: list[Trade] = []
    equity_points: list[float] = []
    daily_cash_factor = (1.0 + execution.cash_yield_annual) ** (1.0 / TRADING_DAYS)

    for today in calendar:
        cash *= daily_cash_factor

        # ---- 1. exits ordered at yesterday's close fill at today's open ----
        if position is not None and position.pending_exit:
            frame = prepared[position.trade.symbol]
            if today in frame.index:
                price = _sell_price(float(frame.at[today, "open"]), execution)
                cash += position.trade.shares * price - execution.commission_per_trade
                position.trade.commission += execution.commission_per_trade
                position.trade.exit_date = today
                position.trade.exit_price = price
                position.trade.exit_reason = position.pending_exit
                trades.append(position.trade)
                position = None

        # ---- 2. entries decided at yesterday's close fill at today's open ----
        if position is None and pending_entry is not None:
            symbol, stop, target = pending_entry
            frame = prepared[symbol]
            if today in frame.index:
                price = _buy_price(float(frame.at[today, "open"]), execution)
                budget = cash * (1.0 - execution.reserve_pct) - execution.commission_per_trade
                shares = math.floor(budget / price) if execution.whole_shares else budget / price
                # A gap straight through the planned stop invalidates the setup.
                if shares > 0 and price > stop:
                    cash -= shares * price + execution.commission_per_trade
                    trade = Trade(
                        symbol=symbol,
                        entry_date=today,
                        entry_price=price,
                        shares=shares,
                        initial_stop=stop,
                        commission=execution.commission_per_trade,
                    )
                    position = _Position(
                        trade=trade,
                        stop=stop,
                        target=target,
                        highest=float(frame.at[today, "high"]),
                    )
        pending_entry = None

        # ---- 3. intrabar stop / target on the open position ----
        if position is not None:
            frame = prepared[position.trade.symbol]
            if today in frame.index:
                bar = frame.loc[today]
                low, high, open_, close = (
                    float(bar["low"]), float(bar["high"]), float(bar["open"]), float(bar["close"])
                )
                hit_stop = low <= position.stop
                hit_target = position.target is not None and high >= position.target

                exit_raw = None
                reason = ""
                if hit_stop:  # assumed to precede the target within the bar
                    exit_raw = position.stop if open_ > position.stop else open_
                    reason = "stop"
                elif hit_target:
                    exit_raw = position.target if open_ < position.target else open_
                    reason = "target"

                if exit_raw is not None:
                    price = _sell_price(exit_raw, execution)
                    cash += position.trade.shares * price - execution.commission_per_trade
                    position.trade.commission += execution.commission_per_trade
                    position.trade.exit_date = today
                    position.trade.exit_price = price
                    position.trade.exit_reason = reason
                    position.trade.bars_held += 1
                    _update_excursions(position, low, high)
                    trades.append(position.trade)
                    position = None
                else:
                    position.trade.bars_held += 1
                    position.highest = max(position.highest, high)
                    _update_excursions(position, low, high)

                    # trail only once the trade has earned it
                    risk = position.trade.risk_per_share
                    if risk > 0 and params.trail_atr_mult > 0:
                        gain_r = (close - position.trade.entry_price) / risk
                        if gain_r >= params.trail_after_r:
                            trail = position.highest - params.trail_atr_mult * float(bar["atr"])
                            position.stop = max(position.stop, trail)

                    # close-based exits act at tomorrow's open
                    if bool(bar["exit_signal"]):
                        position.pending_exit = "signal_exit"
                    elif position.trade.bars_held >= params.max_hold_bars:
                        position.pending_exit = "time_stop"
                    elif params.exit_on_regime_flip and not bool(regime.get(today, True)):
                        position.pending_exit = "regime_off"

        # ---- 4. mark to market ----
        if position is not None:
            frame = prepared[position.trade.symbol]
            last_close = float(frame.at[today, "close"]) if today in frame.index else None
            if last_close is None:
                last_close = float(frame["close"].asof(today))
            equity_points.append(cash + position.trade.shares * last_close)
        else:
            equity_points.append(cash)

        # ---- 5. flat and the market is healthy: pick tomorrow's entry ----
        if position is None and bool(regime.get(today, False)):
            best = book.best(today)
            if best is not None:
                pending_entry = (best.symbol, best.stop, best.target)

    equity = pd.Series(equity_points, index=calendar, name="equity")

    bench_equity = None
    bench_slice = benchmark.loc[calendar]
    if not bench_slice.empty:
        bench_equity = (
            execution.starting_cash * bench_slice["close"] / float(bench_slice["close"].iloc[0])
        ).rename("benchmark")

    open_position = None
    if position is not None:
        last_close = float(prepared[position.trade.symbol]["close"].asof(calendar[-1]))
        open_position = {
            "symbol": position.trade.symbol,
            "entry_date": position.trade.entry_date.date().isoformat(),
            "entry_price": round(position.trade.entry_price, 4),
            "shares": position.trade.shares,
            "initial_stop": round(position.trade.initial_stop, 4),
            "stop": round(position.stop, 4),
            "target": round(position.target, 4) if position.target is not None else None,
            "bars_held": position.trade.bars_held,
            "last_close": round(last_close, 4),
            "open_return_pct": round(last_close / position.trade.entry_price - 1.0, 4),
            "open_r_multiple": round(
                (last_close - position.trade.entry_price) / position.trade.risk_per_share, 3
            ) if position.trade.risk_per_share > 0 else 0.0,
            "pending_exit": position.pending_exit or None,
        }

    result = BacktestResult(
        equity=equity,
        trades=trades,
        benchmark=bench_equity,
        params=config.to_dict(),
        open_position=open_position,
        pending_order=(
            {"symbol": pending_entry[0], "stop": round(pending_entry[1], 4),
             "target": round(pending_entry[2], 4) if pending_entry[2] is not None else None,
             "fill": "next session open"}
            if pending_entry is not None else None
        ),
    )
    result.stats = summarize(result)
    return result


def _update_excursions(position: _Position, low: float, high: float) -> None:
    entry = position.trade.entry_price
    position.trade.mae_pct = min(position.trade.mae_pct, low / entry - 1.0)
    position.trade.mfe_pct = max(position.trade.mfe_pct, high / entry - 1.0)


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def max_drawdown(equity: pd.Series) -> float:
    peak = equity.cummax()
    return float((equity / peak - 1.0).min())


def cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1.0 / years) - 1.0)


def sharpe(equity: pd.Series, risk_free: float = 0.0) -> float:
    rets = equity.pct_change().dropna()
    if rets.std() == 0 or rets.empty:
        return 0.0
    excess = rets - risk_free / TRADING_DAYS
    return float(excess.mean() / excess.std() * np.sqrt(TRADING_DAYS))


def sortino(equity: pd.Series) -> float:
    rets = equity.pct_change().dropna()
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0:
        return 0.0
    return float(rets.mean() / downside.std() * np.sqrt(TRADING_DAYS))


def summarize(result: BacktestResult) -> dict:
    equity = result.equity
    closed = [t for t in result.trades if t.exit_price is not None]
    returns = np.array([t.return_pct for t in closed]) if closed else np.array([])
    r_multiples = np.array([t.r_multiple for t in closed]) if closed else np.array([])
    wins = returns[returns > 0]
    losses = returns[returns <= 0]
    gross_win = float(sum(t.pnl for t in closed if t.pnl > 0))
    gross_loss = float(-sum(t.pnl for t in closed if t.pnl <= 0))
    days_in_market = sum(t.bars_held for t in closed)

    stats = {
        "start": equity.index[0].date().isoformat(),
        "end": equity.index[-1].date().isoformat(),
        "years": round((equity.index[-1] - equity.index[0]).days / 365.25, 2),
        "starting_equity": round(float(equity.iloc[0]), 2),
        "ending_equity": round(float(equity.iloc[-1]), 2),
        "total_return": round(float(equity.iloc[-1] / equity.iloc[0] - 1.0), 4),
        "cagr": round(cagr(equity), 4),
        "max_drawdown": round(max_drawdown(equity), 4),
        "sharpe": round(sharpe(equity), 3),
        "sortino": round(sortino(equity), 3),
        "trades": len(closed),
        "trades_per_year": round(
            len(closed) / max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9), 2
        ),
        "win_rate": round(float(len(wins) / len(returns)), 4) if len(returns) else 0.0,
        "avg_win": round(float(wins.mean()), 4) if len(wins) else 0.0,
        "avg_loss": round(float(losses.mean()), 4) if len(losses) else 0.0,
        "profit_factor": round(gross_win / gross_loss, 3) if gross_loss > 0 else float("inf"),
        "expectancy_r": round(float(r_multiples.mean()), 3) if len(r_multiples) else 0.0,
        "best_trade": round(float(returns.max()), 4) if len(returns) else 0.0,
        "worst_trade": round(float(returns.min()), 4) if len(returns) else 0.0,
        "avg_bars_held": round(float(np.mean([t.bars_held for t in closed])), 1) if closed else 0.0,
        "time_in_market": round(days_in_market / len(equity), 4) if len(equity) else 0.0,
        "exit_reasons": {},
    }
    for trade in closed:
        stats["exit_reasons"][trade.exit_reason] = stats["exit_reasons"].get(trade.exit_reason, 0) + 1

    if result.benchmark is not None and len(result.benchmark) > 1:
        stats["benchmark_total_return"] = round(
            float(result.benchmark.iloc[-1] / result.benchmark.iloc[0] - 1.0), 4
        )
        stats["benchmark_cagr"] = round(cagr(result.benchmark), 4)
        stats["benchmark_max_drawdown"] = round(max_drawdown(result.benchmark), 4)
        stats["benchmark_sharpe"] = round(sharpe(result.benchmark), 3)
    return stats


# Everything the engine and the SignalBook read. Preparing a 200-name
# universe over 20 years costs half a gigabyte if every intermediate
# column is kept, and the walk-forward prepares it once per parameter
# set, so trimming here is what makes that loop fit in memory.
ENGINE_COLUMNS = [
    "open", "high", "low", "close", "atr", "signal", "exit_signal",
    "stop", "stop_pct", "score", "rsi", "rsi_fast", "adx", "mom_long",
]


def prepare_universe(
    bars: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    params: StrategyParams,
    *,
    trim: bool = True,
) -> dict[str, pd.DataFrame]:
    """Feature-prepare every symbol against a shared benchmark.

    `trim` drops the intermediate columns once the signal is built. Keep
    it on for backtests; turn it off when something downstream (the edge
    study, a live scan display) needs the full feature set.
    """
    bench_mom = benchmark_momentum(benchmark, params)
    out = {}
    for symbol, frame in bars.items():
        prepared = prepare(frame, params, bench_mom)
        out[symbol] = prepared[ENGINE_COLUMNS].copy() if trim else prepared
    return out

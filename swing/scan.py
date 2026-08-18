"""Live scanning, paper accounting and the alerts that come out of them.

`run_paper` replays the engine over cached daily bars from the paper
start date to the latest close. That gives, in one pass: the open
position and its current stop, the order (if any) to place at the next
open, and the full closed-trade history -- all produced by the exact code
path the backtest validates.

`intraday_check` is the real-ish-time half: between closes it pulls the
latest quote for the open position and warns when price is at or through
the stop, or through the target, before the bar is finished.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

import pandas as pd

from .alerts import Alert
from .backtest import BacktestResult, prepare_universe, run_backtest
from .config import ExecutionConfig, RunConfig
from .data import get_daily, last_quote, load_many
from .strategy import candidates_on
from .universe import BENCHMARK


@dataclass
class ScanReport:
    asof: pd.Timestamp
    regime_ok: bool
    candidates: list = field(default_factory=list)
    result: BacktestResult | None = None
    alerts: list[Alert] = field(default_factory=list)
    universe_size: int = 0
    notes: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = [
            f"as of close {self.asof.date()}  |  universe {self.universe_size}"
            f"  |  market regime: {'RISK-ON' if self.regime_ok else 'RISK-OFF (stay in cash)'}"
        ]
        if self.result is not None:
            equity = float(self.result.equity.iloc[-1])
            lines.append(f"paper equity: ${equity:,.2f}  ({self.result.stats['total_return']:+.2%})")
            if self.result.open_position:
                position = self.result.open_position
                lines.append(
                    f"holding {position['shares']} {position['symbol']} from "
                    f"{position['entry_date']} @ ${position['entry_price']:,.2f} | "
                    f"stop ${position['stop']:,.2f} | "
                    f"open P/L {position['open_return_pct']:+.2%} "
                    f"({position['open_r_multiple']:+.2f}R)"
                )
            else:
                lines.append("flat / in cash")
            if self.result.pending_order:
                order = self.result.pending_order
                lines.append(
                    f"ORDER for next open: BUY {order['symbol']}, "
                    f"stop ${order['stop']:,.2f}"
                )
        if self.candidates:
            lines.append(f"triggered today ({len(self.candidates)}):")
            for candidate in self.candidates[:10]:
                lines.append(
                    f"  {candidate.symbol:<6} close ${candidate.close:>9,.2f} "
                    f"stop ${candidate.stop:>9,.2f} ({candidate.stop_pct:.1%} risk) "
                    f"score {candidate.score:.3f}  RSI {candidate.rsi:.0f}  ADX {candidate.adx:.0f}"
                )
        elif self.regime_ok:
            lines.append("no setups triggered today")
        for note in self.notes:
            lines.append(f"note: {note}")
        return "\n".join(lines)


def load_market(
    symbols: list[str],
    *,
    start: str | None = None,
    max_age_hours: float | None = 12.0,
    verbose: bool = False,
) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    benchmark = get_daily(BENCHMARK, start=start, max_age_hours=max_age_hours)
    wanted = [s for s in symbols if s != BENCHMARK]
    bars, _ = load_many(wanted, start=start, max_age_hours=max_age_hours, verbose=verbose)
    return bars, benchmark


def run_paper(
    bars: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    config: RunConfig,
    *,
    paper_start: str | pd.Timestamp,
) -> tuple[BacktestResult, dict[str, pd.DataFrame]]:
    prepared = prepare_universe(bars, benchmark, config.params)
    result = run_backtest(
        prepared, benchmark, config, start=pd.Timestamp(paper_start, tz="UTC")
    )
    return result, prepared


def build_alerts(result: BacktestResult, report: ScanReport) -> list[Alert]:
    """Turn the paper account's current state into notifications."""
    alerts: list[Alert] = []
    asof = report.asof.date().isoformat()

    for trade in result.trades:
        if trade.exit_date is None:
            continue
        alerts.append(
            Alert(
                key=f"exit:{trade.symbol}:{trade.entry_date.date()}:{trade.exit_date.date()}",
                kind="exit",
                title=f"CLOSED {trade.symbol} {trade.return_pct:+.2%} ({trade.r_multiple:+.2f}R)",
                body=(
                    f"{trade.symbol}: bought {trade.entry_date.date()} @ "
                    f"${trade.entry_price:,.2f}, sold {trade.exit_date.date()} @ "
                    f"${trade.exit_price:,.2f} on '{trade.exit_reason}' after "
                    f"{trade.bars_held} sessions. P/L ${trade.pnl:,.2f}."
                ),
                urgency="high",
                data=trade.to_row(),
            )
        )

    position = result.open_position
    if position:
        alerts.append(
            Alert(
                key=f"entry:{position['symbol']}:{position['entry_date']}",
                kind="entry",
                title=f"OPENED {position['shares']} {position['symbol']} @ ${position['entry_price']:,.2f}",
                body=(
                    f"Initial stop ${position['initial_stop']:,.2f} "
                    f"({(1 - position['initial_stop'] / position['entry_price']):.2%} risk)."
                    + (f" Target ${position['target']:,.2f}." if position.get("target") else "")
                ),
                urgency="high",
                data=position,
            )
        )
        if position["stop"] > position["initial_stop"]:
            alerts.append(
                Alert(
                    key=f"stop:{position['symbol']}:{position['entry_date']}:{position['stop']}",
                    kind="stop_moved",
                    title=f"STOP RAISED on {position['symbol']} to ${position['stop']:,.2f}",
                    body=(
                        f"Trailing stop now ${position['stop']:,.2f} "
                        f"(was ${position['initial_stop']:,.2f}). "
                        f"Open P/L {position['open_return_pct']:+.2%}."
                    ),
                    data=position,
                )
            )
        if position.get("pending_exit"):
            alerts.append(
                Alert(
                    key=f"exitorder:{position['symbol']}:{asof}",
                    kind="exit",
                    title=f"SELL {position['symbol']} at the next open ({position['pending_exit']})",
                    body=(
                        f"Exit condition '{position['pending_exit']}' triggered on the "
                        f"{asof} close. Sell {position['shares']} shares at tomorrow's open."
                    ),
                    urgency="high",
                    data=position,
                )
            )

    order = result.pending_order
    if order:
        alerts.append(
            Alert(
                key=f"order:{order['symbol']}:{asof}",
                kind="entry",
                title=f"BUY {order['symbol']} at the next open",
                body=(
                    f"Setup triggered on the {asof} close. Buy at the next session's "
                    f"open with the whole account, stop ${order['stop']:,.2f}."
                    + (f" Target ${order['target']:,.2f}." if order.get("target") else "")
                ),
                urgency="high",
                data=order,
            )
        )

    if not result.open_position and not order and report.regime_ok and report.candidates:
        top = report.candidates[0]
        alerts.append(
            Alert(
                key=f"watch:{top.symbol}:{asof}",
                kind="watch",
                title=f"WATCH {top.symbol} (score {top.score:.3f})",
                body=(
                    f"{top.symbol} triggered on the {asof} close at ${top.close:,.2f} "
                    f"with a stop at ${top.stop:,.2f} ({top.stop_pct:.1%} risk)."
                ),
                data=top.as_dict(),
            )
        )
    return alerts


def scan(
    symbols: list[str],
    config: RunConfig,
    *,
    paper_start: str | pd.Timestamp | None = None,
    history_start: str | None = "2015-01-01",
    max_age_hours: float | None = 12.0,
    verbose: bool = False,
) -> ScanReport:
    bars, benchmark = load_market(
        symbols, start=history_start, max_age_hours=max_age_hours, verbose=verbose
    )
    if not bars:
        raise RuntimeError("no symbols loaded -- check connectivity or the universe list")

    params = config.params
    asof = benchmark.index[-1]

    result = None
    prepared = None
    if paper_start is not None:
        result, prepared = run_paper(bars, benchmark, config, paper_start=paper_start)
    else:
        prepared = prepare_universe(bars, benchmark, params)

    from .strategy import compute_regime

    regime = compute_regime(benchmark, params)
    report = ScanReport(
        asof=asof,
        regime_ok=bool(regime.get(asof, False)),
        candidates=candidates_on(prepared, asof, params),
        result=result,
        universe_size=len(bars),
    )
    if result is not None:
        report.alerts = build_alerts(result, report)

    stale = (pd.Timestamp.now(tz="UTC") - asof).days
    if stale > 4:
        report.notes.append(
            f"latest daily bar is {stale} days old -- data may be stale or the market closed"
        )
    return report


def intraday_check(result: BacktestResult, *, tolerance_pct: float = 0.002) -> list[Alert]:
    """Between closes: is the open position at or through its stop/target?"""
    position = result.open_position
    if not position:
        return []

    quote = last_quote(position["symbol"])
    price = quote.get("price")
    if price is None:
        return []

    stamp = quote.get("as_of") or datetime.now(timezone.utc).isoformat(timespec="minutes")
    alerts: list[Alert] = []
    stop, target = position["stop"], position.get("target")

    if price <= stop * (1.0 + tolerance_pct):
        alerts.append(
            Alert(
                key=f"intraday_stop:{position['symbol']}:{stamp[:13]}",
                kind="exit",
                title=f"{position['symbol']} AT STOP ${price:,.2f} (stop ${stop:,.2f})",
                body=(
                    f"{position['symbol']} is trading at ${price:,.2f}, at or below the "
                    f"${stop:,.2f} stop. The rules say sell."
                ),
                urgency="high",
                data={"quote": quote, "position": position},
            )
        )
    elif target and price >= target * (1.0 - tolerance_pct):
        alerts.append(
            Alert(
                key=f"intraday_target:{position['symbol']}:{stamp[:13]}",
                kind="exit",
                title=f"{position['symbol']} AT TARGET ${price:,.2f}",
                body=f"{position['symbol']} reached the ${target:,.2f} target.",
                urgency="high",
                data={"quote": quote, "position": position},
            )
        )
    else:
        gain = price / position["entry_price"] - 1.0
        alerts.append(
            Alert(
                key=f"intraday_ok:{position['symbol']}:{stamp[:13]}",
                kind="info",
                title=f"{position['symbol']} ${price:,.2f} ({gain:+.2%})",
                body=f"Stop ${stop:,.2f}. No action.",
                data={"quote": quote, "position": position},
            )
        )
    return alerts

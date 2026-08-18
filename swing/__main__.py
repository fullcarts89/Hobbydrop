"""Command line entry point: python -m swing <command>."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd

from .alerts import Alert, build_notifier
from .backtest import prepare_universe, run_backtest
from .config import ExecutionConfig, RunConfig, StrategyParams
from .data import load_many, get_daily
from .research import signal_edge
from .scan import intraday_check, run_paper, scan
from .state import PaperState
from .strategy import SignalBook
from .universe import BENCHMARK, load_universe
from .walkforward import DEFAULT_GRID, bootstrap_trades, walk_forward


def _config_from_args(args) -> RunConfig:
    if getattr(args, "config", None):
        config = RunConfig.load(args.config)
    else:
        config = RunConfig()
    overrides = {}
    for key in ("entry_mode", "oversold_rsi", "min_momentum", "stop_atr_mult", "max_hold_bars"):
        value = getattr(args, key, None)
        if value is not None:
            overrides[key] = value
    params = config.params.evolve(**overrides) if overrides else config.params

    execution = config.execution
    exec_overrides = {}
    if getattr(args, "cash", None) is not None:
        exec_overrides["starting_cash"] = args.cash
    if getattr(args, "slippage_bps", None) is not None:
        exec_overrides["slippage_bps"] = args.slippage_bps
    if exec_overrides:
        execution = ExecutionConfig(**{**execution.__dict__, **exec_overrides})
    return RunConfig(params=params, execution=execution)


def _load(args, config: RunConfig):
    symbols = load_universe(args.universe)
    benchmark = get_daily(BENCHMARK, max_age_hours=args.max_age_hours)
    bars, stats = load_many(
        [s for s in symbols if s != BENCHMARK],
        max_age_hours=args.max_age_hours,
        min_bars=config.params.warmup_bars,
        verbose=args.verbose,
    )
    if not bars:
        raise SystemExit("no symbols loaded -- check connectivity or the universe list")
    if args.verbose:
        print(f"loaded {stats.hits} symbols ({stats.failures} unavailable)")
    return bars, benchmark


def _print_stats(stats: dict) -> None:
    order = [
        ("period", f"{stats['start']} -> {stats['end']} ({stats['years']}y)"),
        ("equity", f"${stats['starting_equity']:,.0f} -> ${stats['ending_equity']:,.0f}"),
        ("total return", f"{stats['total_return']:+.1%}"),
        ("CAGR", f"{stats['cagr']:+.2%}"),
        ("max drawdown", f"{stats['max_drawdown']:.1%}"),
        ("Sharpe", f"{stats['sharpe']:.2f}"),
        ("trades", f"{stats['trades']} ({stats['trades_per_year']}/yr)"),
        ("win rate", f"{stats['win_rate']:.1%}"),
        ("avg win / avg loss", f"{stats['avg_win']:+.2%} / {stats['avg_loss']:+.2%}"),
        ("profit factor", f"{stats['profit_factor']}"),
        ("expectancy", f"{stats['expectancy_r']:+.3f} R"),
        ("avg hold", f"{stats['avg_bars_held']} sessions"),
        ("time in market", f"{stats['time_in_market']:.0%}"),
        ("exits", ", ".join(f"{k}={v}" for k, v in sorted(stats["exit_reasons"].items()))),
    ]
    if "benchmark_cagr" in stats:
        order.append(
            (
                f"{BENCHMARK} buy & hold",
                f"{stats['benchmark_total_return']:+.1%} total, "
                f"{stats['benchmark_cagr']:+.2%} CAGR, "
                f"{stats['benchmark_max_drawdown']:.1%} max DD, "
                f"Sharpe {stats['benchmark_sharpe']:.2f}",
            )
        )
    width = max(len(label) for label, _ in order)
    for label, value in order:
        print(f"  {label:<{width}}  {value}")


# ---------------------------------------------------------------- commands

def cmd_fetch(args) -> int:
    config = _config_from_args(args)
    bars, _ = _load(args, config)
    print(f"cached {len(bars)} symbols + {BENCHMARK}")
    return 0


def cmd_backtest(args) -> int:
    config = _config_from_args(args)
    bars, benchmark = _load(args, config)
    prepared = prepare_universe(bars, benchmark, config.params)
    book = SignalBook(prepared, config.params)
    start = pd.Timestamp(args.start, tz="UTC") if args.start else None
    end = pd.Timestamp(args.end, tz="UTC") if args.end else None
    result = run_backtest(prepared, benchmark, config, start=start, end=end, book=book)

    print(f"\nbacktest  entry_mode={config.params.entry_mode}  universe={len(bars)}  "
          f"signals={len(book)}")
    _print_stats(result.stats)

    if result.open_position:
        print(f"\n  still holding: {json.dumps(result.open_position)}")
    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        result.blotter().to_csv(out / "trades.csv", index=False)
        result.equity.to_csv(out / "equity.csv")
        (out / "stats.json").write_text(json.dumps(result.stats, indent=2) + "\n")
        config.save(out / "config.json")
        print(f"\n  wrote {out}/trades.csv, equity.csv, stats.json, config.json")
    return 0


def cmd_walkforward(args) -> int:
    config = _config_from_args(args)
    bars, benchmark = _load(args, config)
    grid = json.loads(Path(args.grid).read_text()) if args.grid else DEFAULT_GRID
    outcome = walk_forward(
        bars,
        benchmark,
        config,
        grid=grid,
        train_years=args.train_years,
        test_years=args.test_years,
        start=args.start,
        verbose=True,
    )
    oos = outcome["oos"]
    print("\nout-of-sample only (parameters always chosen before the fact):")
    _print_stats(oos.stats)

    boot = bootstrap_trades(
        oos.trades, starting_cash=config.execution.starting_cash, samples=args.bootstrap
    )
    if boot.get("samples"):
        print("\ntrade-order bootstrap (same trades, reshuffled):")
        print(f"  median outcome        ${boot['median_final']:,.0f}")
        print(f"  5th / 95th percentile ${boot['p05_final']:,.0f} / ${boot['p95_final']:,.0f}")
        print(f"  chance of losing money {boot['prob_loss']:.1%}")
        print(f"  median worst drawdown {boot['median_max_drawdown']:.1%}"
              f"  (5th pct {boot['p05_max_drawdown']:.1%})")
        print(f"  chance of a >30% drawdown {boot['prob_drawdown_over_30pct']:.1%}"
              f" | >50% {boot['prob_drawdown_over_50pct']:.1%}")

    print("\nper fold:")
    print(outcome["fold_table"].to_string(index=False))

    if args.out:
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        oos.blotter().to_csv(out / "oos_trades.csv", index=False)
        oos.equity.to_csv(out / "oos_equity.csv")
        outcome["fold_table"].to_csv(out / "folds.csv", index=False)
        (out / "oos_stats.json").write_text(
            json.dumps({"stats": oos.stats, "bootstrap": boot}, indent=2) + "\n"
        )
        print(f"\n  wrote {out}/oos_trades.csv, oos_equity.csv, folds.csv, oos_stats.json")
    return 0


def cmd_edge(args) -> int:
    config = _config_from_args(args)
    bars, benchmark = _load(args, config)
    # the control condition needs the full feature set, not the lean one
    prepared = prepare_universe(bars, benchmark, config.params, trim=False)
    report = signal_edge(prepared, benchmark, config.params, start=args.start)
    print(f"\nsignal edge study  entry_mode={config.params.entry_mode}  "
          f"signals={report.signals}  control observations={report.control_signals}")
    print("(edge_vs_control is the number that matters -- excess over simply")
    print(" holding any liquid uptrending name on the same days)\n")
    print(report.table.to_string())
    return 0


def cmd_scan(args) -> int:
    config = _config_from_args(args)
    symbols = load_universe(args.universe)
    state = PaperState.load(args.state)
    if args.paper_start:
        state.paper_start = args.paper_start
    if state.paper_start is None:
        state.paper_start = (pd.Timestamp.utcnow() - pd.Timedelta(days=365)).date().isoformat()
    state.starting_cash = config.execution.starting_cash

    report = scan(
        symbols,
        config,
        paper_start=state.paper_start,
        max_age_hours=args.max_age_hours,
        verbose=args.verbose,
    )
    print(report.summary())

    notifier = build_notifier(
        console=False, jsonl_path=args.alert_log, webhook_url=args.webhook, email_to=args.email
    )

    first_run = state.last_run is None
    if first_run and not args.backfill:
        # The paper account is replayed from `paper_start` on every run, so a
        # first run would otherwise fire one alert per historical trade.
        for alert in report.alerts:
            state.mark_sent(alert.key)
        print(f"\nseeded {len(report.alerts)} historical event(s) without notifying "
              f"(use --backfill to send them). Future runs alert on new events only.")
        if not args.dry_run:
            state.save()
        return 0

    fresh = state.filter_new(report.alerts)
    if fresh:
        print(f"\n{len(fresh)} new alert(s):")
        for alert in fresh:
            print(f"\n{alert.as_text()}")
        notifier.send_all(fresh)
    else:
        print("\nno new alerts since the last run")
    for error in notifier.errors:
        print(f"  alert delivery failed -- {error}", file=sys.stderr)

    if not args.dry_run:
        state.save()
    return 0


def cmd_watch(args) -> int:
    """Poll during the session so a stop is not discovered at tomorrow's close."""
    config = _config_from_args(args)
    symbols = load_universe(args.universe)
    state = PaperState.load(args.state)
    if state.paper_start is None:
        state.paper_start = (pd.Timestamp.utcnow() - pd.Timedelta(days=365)).date().isoformat()

    notifier = build_notifier(
        console=False, jsonl_path=args.alert_log, webhook_url=args.webhook, email_to=args.email
    )
    bars, benchmark = _load(args, config)
    deadline = time.time() + args.max_minutes * 60

    while True:
        result, _ = run_paper(bars, benchmark, config, paper_start=state.paper_start)
        alerts = intraday_check(result)
        fresh = [a for a in alerts if a.kind != "info" and state.is_new(a.key)]
        for alert in alerts:
            print(f"[{time.strftime('%H:%M:%S')}] {alert.title}")
        if fresh:
            for alert in fresh:
                state.mark_sent(alert.key)
            notifier.send_all(fresh)
            state.save()
        if args.once or time.time() >= deadline:
            break
        time.sleep(args.interval)
    state.save()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swing", description=__doc__)
    parser.add_argument("--universe", default="liquid2004",
                        help="preset (liquid2004|modern|all), a file, or a ticker list")
    parser.add_argument("--config", help="path to a saved config.json")
    parser.add_argument("--cash", type=float, help="starting account size")
    parser.add_argument("--slippage-bps", dest="slippage_bps", type=float)
    parser.add_argument("--entry-mode", dest="entry_mode", choices=("oversold", "reclaim"))
    parser.add_argument("--oversold-rsi", dest="oversold_rsi", type=float)
    parser.add_argument("--min-momentum", dest="min_momentum", type=float)
    parser.add_argument("--stop-atr-mult", dest="stop_atr_mult", type=float)
    parser.add_argument("--max-hold-bars", dest="max_hold_bars", type=int)
    parser.add_argument("--max-age-hours", dest="max_age_hours", type=float, default=12.0,
                        help="reuse cached bars younger than this (0 forces a refetch)")
    parser.add_argument("-v", "--verbose", action="store_true")

    subparsers = parser.add_subparsers(dest="command", required=True)

    sub = subparsers.add_parser("fetch", help="warm the local bar cache")
    sub.set_defaults(func=cmd_fetch)

    sub = subparsers.add_parser("backtest", help="single-pass historical simulation")
    sub.add_argument("--start", default="2005-01-01")
    sub.add_argument("--end")
    sub.add_argument("--out", help="directory for trades.csv / equity.csv / stats.json")
    sub.set_defaults(func=cmd_backtest)

    sub = subparsers.add_parser("walkforward", help="out-of-sample validation (the honest one)")
    sub.add_argument("--start", default="2005-01-01")
    sub.add_argument("--train-years", dest="train_years", type=float, default=6.0)
    sub.add_argument("--test-years", dest="test_years", type=float, default=2.0)
    sub.add_argument("--grid", help="path to a JSON parameter grid")
    sub.add_argument("--bootstrap", type=int, default=2000)
    sub.add_argument("--out")
    sub.set_defaults(func=cmd_walkforward)

    sub = subparsers.add_parser("edge", help="forward-return study of the entry signal")
    sub.add_argument("--start", default="2005-01-01")
    sub.set_defaults(func=cmd_edge)

    sub = subparsers.add_parser("scan", help="today's signals, paper state and alerts")
    sub.add_argument("--paper-start", dest="paper_start")
    sub.add_argument("--state", default="state/paper.json")
    sub.add_argument("--alert-log", dest="alert_log", default="state/alerts.jsonl")
    sub.add_argument("--webhook", help="Slack/Discord webhook URL (or SWING_WEBHOOK_URL)")
    sub.add_argument("--email", help="destination address (or SWING_EMAIL_TO)")
    sub.add_argument("--dry-run", dest="dry_run", action="store_true",
                     help="do not record which alerts were sent")
    sub.add_argument("--backfill", action="store_true",
                     help="on the first run, notify for the whole replayed history too")
    sub.set_defaults(func=cmd_scan)

    sub = subparsers.add_parser("watch", help="intraday stop/target monitor")
    sub.add_argument("--state", default="state/paper.json")
    sub.add_argument("--alert-log", dest="alert_log", default="state/alerts.jsonl")
    sub.add_argument("--webhook")
    sub.add_argument("--email")
    sub.add_argument("--interval", type=int, default=300, help="seconds between polls")
    sub.add_argument("--max-minutes", dest="max_minutes", type=float, default=420.0)
    sub.add_argument("--once", action="store_true")
    sub.set_defaults(func=cmd_watch)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.max_age_hours == 0:
        args.max_age_hours = None
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())

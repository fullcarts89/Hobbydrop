"""Out-of-sample validation.

A backtest you tuned on the whole history tells you almost nothing. This
module does two things instead:

1. **Walk-forward.** Chop the history into consecutive folds. For each
   fold, pick parameters using only the years *before* it, then trade the
   fold with those parameters and keep only that result. Splicing the
   fold results together gives an equity curve where every single trade
   was taken with parameters chosen before the fact.

2. **Trade bootstrap.** Resample the realised trades to show what the
   same edge could have produced in a different order. For an all-in
   strategy the ordering of trades drives the drawdown, and a single
   historical path badly understates how bad it can get.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .backtest import BacktestResult, max_drawdown, prepare_universe, run_backtest, summarize
from .config import RunConfig, StrategyParams
from .strategy import SignalBook

# A deliberately small grid. Every extra knob buys a little in-sample
# performance and costs out-of-sample credibility.
DEFAULT_GRID: dict[str, list] = {
    "oversold_rsi": [5.0, 10.0, 15.0],     # how deep a washout to require
    "min_momentum": [0.10, 0.20, 0.35],    # how strong the uptrend must be
    "exit_rsi": [70.0, 80.0],              # how far to let the bounce run
}


@dataclass
class Fold:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    chosen: dict = field(default_factory=dict)
    train_score: float = 0.0
    test_stats: dict = field(default_factory=dict)

    def to_row(self) -> dict:
        row = {
            "train": f"{self.train_start.date()}..{self.train_end.date()}",
            "test": f"{self.test_start.date()}..{self.test_end.date()}",
            "train_score": round(self.train_score, 3),
        }
        row.update({f"p_{k}": v for k, v in self.chosen.items()})
        for key in ("total_return", "cagr", "max_drawdown", "trades", "win_rate", "expectancy_r"):
            row[key] = self.test_stats.get(key)
        return row


def make_folds(
    calendar: pd.DatetimeIndex,
    *,
    train_years: float = 6.0,
    test_years: float = 2.0,
    warmup_years: float = 1.0,
) -> list[Fold]:
    """Rolling train/test splits, oldest first."""
    start = calendar[0] + pd.Timedelta(days=int(warmup_years * 365.25))
    end = calendar[-1]
    folds: list[Fold] = []
    train_delta = pd.Timedelta(days=int(train_years * 365.25))
    test_delta = pd.Timedelta(days=int(test_years * 365.25))

    train_start = start
    while True:
        train_end = train_start + train_delta
        test_start = train_end
        test_end = min(test_start + test_delta, end)
        if test_start >= end or (test_end - test_start) < pd.Timedelta(days=180):
            break
        folds.append(Fold(train_start, train_end, test_start, test_end))
        train_start = train_start + test_delta
    return folds


def objective(stats: dict, *, min_trades: int = 8) -> float:
    """MAR-style score: annual return per unit of peak-to-trough pain."""
    if stats.get("trades", 0) < min_trades:
        return -np.inf
    drawdown = abs(stats.get("max_drawdown", 0.0))
    return stats.get("cagr", 0.0) / max(drawdown, 0.05)


def grid_combinations(grid: dict[str, list]) -> list[dict]:
    keys = sorted(grid)
    return [dict(zip(keys, values)) for values in itertools.product(*(grid[k] for k in keys))]


def walk_forward(
    bars: dict[str, pd.DataFrame],
    benchmark: pd.DataFrame,
    base: RunConfig,
    *,
    grid: dict[str, list] | None = None,
    train_years: float = 6.0,
    test_years: float = 2.0,
    start: str | pd.Timestamp | None = None,
    verbose: bool = True,
) -> dict:
    """Run the walk-forward and return folds plus a spliced OOS result."""
    grid = grid or DEFAULT_GRID
    combos = grid_combinations(grid)

    calendar = benchmark.index
    if start is not None:
        calendar = calendar[calendar >= pd.Timestamp(start, tz="UTC")]
    folds = make_folds(calendar, train_years=train_years, test_years=test_years)
    if not folds:
        raise ValueError("history too short for the requested fold sizes")

    # Features are causal, so one preparation per parameter set covers
    # every fold -- no leakage from preparing over the full history. The
    # loop is ordered parameters-outer / folds-inner so only a single
    # prepared universe is alive at a time; keeping one per parameter set
    # costs about half a gigabyte each.
    def build(combo: dict):
        config = RunConfig(params=base.params.evolve(**combo), execution=base.execution)
        prepared = prepare_universe(bars, benchmark, config.params)
        return config, prepared, SignalBook(prepared, config.params)

    if verbose:
        print(f"walk-forward: {len(folds)} folds x {len(combos)} parameter sets")

    # --- pass 1: score every parameter set on every fold's training window ---
    scores = np.full((len(folds), len(combos)), -np.inf)
    for combo_index, combo in enumerate(combos):
        config, prepared, book = build(combo)
        for fold_index, fold in enumerate(folds):
            try:
                trial = run_backtest(
                    prepared, benchmark, config,
                    start=fold.train_start, end=fold.train_end, book=book,
                )
            except ValueError:
                continue
            scores[fold_index, combo_index] = objective(trial.stats)
        del prepared, book
        if verbose:
            print(f"  scored parameter set {combo_index + 1}/{len(combos)}: {combo}")

    for fold_index, fold in enumerate(folds):
        best = int(np.argmax(scores[fold_index]))
        fold.chosen = combos[best]
        chosen_score = scores[fold_index, best]
        fold.train_score = float(chosen_score) if np.isfinite(chosen_score) else 0.0

    # --- pass 2: trade each fold with the parameters its training window chose ---
    equity_pieces: list[pd.Series] = []
    all_trades = []
    running_equity = base.execution.starting_cash
    cached_key, cached = None, None

    for index, fold in enumerate(folds, start=1):
        key = tuple(sorted(fold.chosen.items()))
        if key != cached_key:
            cached = build(fold.chosen)
            cached_key = key
        config, prepared, book = cached

        oos_config = RunConfig(
            params=config.params,
            execution=type(base.execution)(
                **{**base.execution.__dict__, "starting_cash": running_equity}
            ),
        )
        oos = run_backtest(
            prepared, benchmark, oos_config,
            start=fold.test_start, end=fold.test_end, book=book,
        )
        fold.test_stats = oos.stats
        running_equity = float(oos.equity.iloc[-1])
        equity_pieces.append(oos.equity)
        all_trades.extend(oos.trades)

        if verbose:
            print(
                f"  fold {index}/{len(folds)} test {fold.test_start.date()}..{fold.test_end.date()} "
                f"-> {oos.stats['total_return']:+.1%} "
                f"(dd {oos.stats['max_drawdown']:.1%}, {oos.stats['trades']} trades) "
                f"params {fold.chosen}"
            )

    spliced = pd.concat(equity_pieces)
    spliced = spliced[~spliced.index.duplicated(keep="last")].sort_index()

    bench_slice = benchmark.loc[
        (benchmark.index >= spliced.index[0]) & (benchmark.index <= spliced.index[-1])
    ]
    bench_equity = (
        base.execution.starting_cash * bench_slice["close"] / float(bench_slice["close"].iloc[0])
    ).rename("benchmark")

    stitched = BacktestResult(
        equity=spliced, trades=all_trades, benchmark=bench_equity, params=base.to_dict()
    )
    stitched.stats = summarize(stitched)

    return {
        "folds": folds,
        "oos": stitched,
        "fold_table": pd.DataFrame([f.to_row() for f in folds]),
    }


def bootstrap_trades(
    trades,
    *,
    starting_cash: float = 25_000.0,
    samples: int = 2000,
    seed: int = 7,
) -> dict:
    """Resample trade returns to get a distribution instead of one path."""
    returns = np.array([t.return_pct for t in trades if t.exit_price is not None])
    if len(returns) < 5:
        return {"samples": 0}

    rng = np.random.default_rng(seed)
    draws = rng.choice(returns, size=(samples, len(returns)), replace=True)
    curves = np.cumprod(1.0 + draws, axis=1) * starting_cash

    finals = curves[:, -1]
    peaks = np.maximum.accumulate(curves, axis=1)
    drawdowns = (curves / peaks - 1.0).min(axis=1)

    return {
        "samples": samples,
        "trades_per_path": int(len(returns)),
        "median_final": round(float(np.median(finals)), 2),
        "p05_final": round(float(np.percentile(finals, 5)), 2),
        "p95_final": round(float(np.percentile(finals, 95)), 2),
        "prob_loss": round(float((finals < starting_cash).mean()), 4),
        "median_max_drawdown": round(float(np.median(drawdowns)), 4),
        "p05_max_drawdown": round(float(np.percentile(drawdowns, 5)), 4),
        "worst_max_drawdown": round(float(drawdowns.min()), 4),
        "prob_drawdown_over_30pct": round(float((drawdowns < -0.30).mean()), 4),
        "prob_drawdown_over_50pct": round(float((drawdowns < -0.50).mean()), 4),
    }

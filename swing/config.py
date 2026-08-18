"""Tunable parameters.

Kept in one place so the walk-forward optimiser can perturb them and so a
live scan provably runs the same numbers the backtest validated.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path


@dataclass(frozen=True)
class StrategyParams:
    # --- which entry trigger to use ---
    # "oversold": buy short-term weakness inside a strong uptrend (default;
    #             this is the variant that showed a measurable edge).
    # "reclaim":  buy the first close above the prior day's high after a dip
    #             (the textbook pullback entry -- kept so the comparison in
    #             the README can be re-run, not because it tested well).
    entry_mode: str = "oversold"

    # --- moving averages / trend ---
    sma_fast: int = 10
    sma_mid: int = 50
    sma_slow: int = 200
    slope_lookback: int = 20

    # --- indicator lengths ---
    atr_length: int = 14
    rsi_length: int = 14
    rsi_fast_length: int = 2
    adx_length: int = 14
    momentum_lookback: int = 126      # ~6 months
    momentum_short: int = 21          # ~1 month
    pullback_lookback: int = 10
    swing_low_lookback: int = 10
    breakout_lookback: int = 20

    # --- tradability filters ---
    min_price: float = 10.0
    min_dollar_volume: float = 20_000_000.0
    min_atr_pct: float = 0.010
    max_atr_pct: float = 0.090

    # --- trend / momentum thresholds ---
    min_adx: float = 0.0
    min_momentum: float = 0.20        # 6m return floor
    require_relative_strength: bool = True

    # --- "oversold" trigger ---
    oversold_rsi: float = 10.0        # RSI(2) below this is the entry
    exit_rsi: float = 70.0            # RSI(2) back above this closes the trade

    # --- "reclaim" trigger ---
    pullback_rsi: float = 45.0        # RSI must have dipped at least this low
    min_pullback_atr: float = 1.0     # ...or price pulled back this many ATRs
    trigger_window: int = 8           # bars allowed between dip and trigger
    max_extension_atr: float = 2.5    # do not chase far above the 10-day MA

    # --- risk ---
    stop_atr_mult: float = 2.5
    max_stop_pct: float = 0.12        # all-in, so stop distance IS position size
    target_r: float = 0.0             # 0 disables the fixed target
    trail_atr_mult: float = 0.0       # 0 disables the trail (holds are short)
    trail_after_r: float = 1.0        # trail only activates past +1R
    max_hold_bars: int = 10
    exit_below_ma: str = ""           # "reclaim" mode uses "sma_mid"

    # --- regime ---
    regime_symbol: str = "SPY"
    regime_ma: int = 200
    exit_on_regime_flip: bool = True

    # --- ranking when several names trigger the same day ---
    # Weighting a tight stop actively hurt: it biases the pick toward the
    # lowest-volatility candidate, which historically also had the lowest
    # forward return. Trend quality and momentum are what is left.
    weight_momentum: float = 0.5
    weight_tightness: float = 0.0
    weight_trend: float = 0.5

    @property
    def warmup_bars(self) -> int:
        return max(self.sma_slow, self.momentum_lookback, self.regime_ma) + 10

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "StrategyParams":
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown strategy params: {sorted(unknown)}")
        return cls(**data)

    def evolve(self, **kwargs) -> "StrategyParams":
        return replace(self, **kwargs)


@dataclass(frozen=True)
class ExecutionConfig:
    """How orders are assumed to fill. Defaults are deliberately pessimistic."""

    starting_cash: float = 25_000.0
    slippage_bps: float = 10.0        # 0.10% each way
    commission_per_trade: float = 0.0
    cash_yield_annual: float = 0.0    # idle cash earns nothing by default
    whole_shares: bool = True
    reserve_pct: float = 0.005        # leave a sliver so an order never bounces


@dataclass(frozen=True)
class RunConfig:
    params: StrategyParams = StrategyParams()
    execution: ExecutionConfig = ExecutionConfig()

    def to_dict(self) -> dict:
        return {"params": asdict(self.params), "execution": asdict(self.execution)}

    @classmethod
    def from_dict(cls, data: dict) -> "RunConfig":
        return cls(
            params=StrategyParams.from_dict(data.get("params", {})),
            execution=ExecutionConfig(**data.get("execution", {})),
        )

    @classmethod
    def load(cls, path: str | Path) -> "RunConfig":
        return cls.from_dict(json.loads(Path(path).read_text()))

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n")

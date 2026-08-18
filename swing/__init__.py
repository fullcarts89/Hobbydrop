"""Swing-trading research and alerting toolkit.

A single-position, cash-only swing system: the same code generates the
historical paper trades and the live alerts, so what you are alerted to
is what was tested.
"""

from .config import ExecutionConfig, RunConfig, StrategyParams

__version__ = "0.1.0"
__all__ = ["RunConfig", "StrategyParams", "ExecutionConfig", "__version__"]

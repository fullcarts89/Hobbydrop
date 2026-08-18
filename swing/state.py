"""Persistent state for the live/paper loop.

The paper account itself is *not* stored -- it is recomputed from cached
bars on every run by the same engine the backtest uses, so paper results
and backtest results can never drift apart. What is stored is only the
bookkeeping the recomputation cannot derive: which alerts have already
gone out, and when the account started.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_STATE_PATH = Path("state/paper.json")


@dataclass
class PaperState:
    path: Path = DEFAULT_STATE_PATH
    paper_start: str | None = None
    starting_cash: float = 25_000.0
    sent_keys: list[str] = field(default_factory=list)
    last_run: str | None = None
    max_sent_keys: int = 2000

    @classmethod
    def load(cls, path: str | Path = DEFAULT_STATE_PATH) -> "PaperState":
        path = Path(path)
        if not path.exists():
            return cls(path=path)
        data = json.loads(path.read_text())
        return cls(
            path=path,
            paper_start=data.get("paper_start"),
            starting_cash=float(data.get("starting_cash", 25_000.0)),
            sent_keys=list(data.get("sent_keys", [])),
            last_run=data.get("last_run"),
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.last_run = datetime.now(timezone.utc).isoformat(timespec="seconds")
        payload = {
            "paper_start": self.paper_start,
            "starting_cash": self.starting_cash,
            "sent_keys": self.sent_keys[-self.max_sent_keys :],
            "last_run": self.last_run,
        }
        self.path.write_text(json.dumps(payload, indent=2) + "\n")

    def is_new(self, key: str) -> bool:
        return key not in self.sent_keys

    def mark_sent(self, key: str) -> None:
        if key not in self.sent_keys:
            self.sent_keys.append(key)

    def filter_new(self, alerts) -> list:
        fresh = [a for a in alerts if self.is_new(a.key)]
        for alert in fresh:
            self.mark_sent(alert.key)
        return fresh

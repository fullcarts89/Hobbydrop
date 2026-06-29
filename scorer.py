"""Conviction scoring model (max 100 points).

Form 4 open-market purchases and 13D/13G accumulations are scored on the same
100-point scale, but a few axes interpret the inputs differently per form type
(e.g. "intent" and "cluster/new position"). See the README for the rationale
behind each band.
"""
from __future__ import annotations

from models import Filing

# Role/title -> seniority points (axis 3). Checked longest-match-first.
_ROLE_MAP = [
    ("chief executive", 18), ("ceo", 18),
    ("chief financial", 16), ("cfo", 16),
    ("president", 15),
    ("chief operating", 14), ("coo", 14),
    ("10% owner", 14), ("10%", 14),
    ("director", 10),
    ("vice president", 6), ("vp", 6),
]


def _match_role(title: str, default: int = 4) -> int:
    t = (title or "").lower()
    for needle, pts in _ROLE_MAP:
        if needle in t:
            return pts
    return default


def _relative_size_points(rel_pct: float | None) -> int:
    if rel_pct is None:
        return 0
    if rel_pct >= 5:
        return 25
    if rel_pct >= 2:
        return 20
    if rel_pct >= 1:
        return 15
    if rel_pct >= 0.5:
        return 10
    if rel_pct >= 0.25:
        return 5
    return 0


def _news_vacuum_points(days: int) -> int:
    if days >= 60:
        return 20
    if days >= 30:
        return 14
    if days >= 14:
        return 8
    if days >= 7:
        return 4
    return 0


def _filer_quality_points(filing: Filing) -> int:
    if filing.filing_type in ("13D", "13G"):
        return {"corporation": 14, "individual": 10, "fund": 8}.get(filing.filer_kind, 8)
    return _match_role(filing.insider_title, default=4)


def _cluster_points(filing: Filing) -> int:
    if filing.cluster_count >= 3:
        return 14
    if filing.cluster_count == 2:
        return 10
    if filing.is_new_position:  # 13D: first reported position
        return 8
    if filing.cluster_count == 1:
        return 4
    return 0


def _intent_points(filing: Filing) -> int:
    if filing.is_first_open_market_purchase:
        return 13
    if filing.filing_type == "13D":
        return 10
    if filing.filing_type == "13G":
        return 4
    return 6


def _window_points(delta: float | None) -> int:
    """Trade-to-now price window (axis 6). ``delta`` is signed % move."""
    if delta is None:
        return 0
    if abs(delta) < 5:            # still near the insider's entry — best
        return 10
    if 5 <= delta < 20:          # moved up but not gone
        return 6
    if delta <= -5:              # underwater vs entry
        return 4
    return 0                      # ran > 20% — window closed


def score_filing(filing: Filing) -> tuple[int, dict]:
    breakdown = {
        "relative_size": _relative_size_points(filing.rel_pct),
        "news_vacuum": _news_vacuum_points(filing.days_since_last_8k),
        "filer_quality": _filer_quality_points(filing),
        "cluster_or_new": _cluster_points(filing),
        "intent": _intent_points(filing),
        "window": _window_points(filing.price_delta_pct),
    }
    total = sum(breakdown.values())
    filing.score = total
    filing.breakdown = breakdown
    return total, breakdown

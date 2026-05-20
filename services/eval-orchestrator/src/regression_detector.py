"""Regression detection (FR-RD-1..3).

Scaffolded in Phase C; the full periodic job + candidate-cause analysis + OTel
emission is implemented in Phase F. The detection math lives here so it can be
unit-tested independently of scheduling.
"""

from __future__ import annotations

from datetime import datetime, timezone
from statistics import StatisticsError, mean, pstdev

# Trigger thresholds (FR-RD-1).
STDDEV_TRIGGER = 2.0
ABSOLUTE_DROP_TRIGGER = 0.10


def is_regression(baseline_scores: list[float], current_scores: list[float]) -> tuple[bool, float]:
    """Return (regressed, delta).

    Regressed when the current window mean is >2σ below the baseline mean, or the
    absolute drop exceeds 10 percentage points.
    """
    if not baseline_scores or not current_scores:
        return False, 0.0
    baseline_mean = mean(baseline_scores)
    current_mean = mean(current_scores)
    delta = current_mean - baseline_mean
    if -delta >= ABSOLUTE_DROP_TRIGGER:
        return True, round(delta, 4)
    try:
        sigma = pstdev(baseline_scores)
    except StatisticsError:
        sigma = 0.0
    if sigma > 0 and current_mean < baseline_mean - STDDEV_TRIGGER * sigma:
        return True, round(delta, 4)
    return False, round(delta, 4)


def _parse_ts(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def rank_candidate_causes(
    change_events: list[dict], onset: datetime, top_n: int = 5
) -> list[dict]:
    """Rank change events by temporal proximity to the regression onset (FR-RD-2).

    Returns the top-N closest events as ranked candidate causes. Events are
    assumed to already be scoped to the affected agent.
    """
    scored: list[tuple[float, dict]] = []
    for ev in change_events:
        ts = ev.get("timestamp")
        if not ts:
            continue
        try:
            event_time = _parse_ts(ts)
        except (ValueError, TypeError):
            continue
        proximity_hours = abs((event_time - onset).total_seconds()) / 3600.0
        scored.append((proximity_hours, ev))

    scored.sort(key=lambda pair: pair[0])
    causes: list[dict] = []
    for rank, (proximity_hours, ev) in enumerate(scored[:top_n], start=1):
        causes.append(
            {
                "rank": rank,
                "event_id": ev.get("id"),
                "event_type": ev.get("event_type"),
                "reason": ev.get("reason"),
                "timestamp": ev.get("timestamp"),
                "proximity_hours": round(proximity_hours, 1),
            }
        )
    return causes

"""Regression detection (FR-RD-1..3).

Scaffolded in Phase C; the full periodic job + candidate-cause analysis + OTel
emission is implemented in Phase F. The detection math lives here so it can be
unit-tested independently of scheduling.
"""

from __future__ import annotations

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

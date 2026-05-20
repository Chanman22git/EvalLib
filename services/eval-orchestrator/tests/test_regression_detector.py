from __future__ import annotations

from src.regression_detector import is_regression


def test_no_regression_when_stable():
    regressed, delta = is_regression([0.9, 0.91, 0.89], [0.9, 0.92, 0.88])
    assert regressed is False
    assert abs(delta) < 0.05


def test_absolute_drop_triggers():
    regressed, delta = is_regression([0.9, 0.9, 0.9], [0.75, 0.74, 0.76])
    assert regressed is True
    assert delta < -0.10


def test_stddev_drop_triggers_on_tight_baseline():
    # Baseline tightly clustered near 0.90; a drop to ~0.86 is >2σ below.
    regressed, _ = is_regression([0.90, 0.90, 0.91, 0.89, 0.90], [0.86, 0.86, 0.85])
    assert regressed is True


def test_empty_inputs_safe():
    assert is_regression([], [0.5]) == (False, 0.0)

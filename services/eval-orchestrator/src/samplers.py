from __future__ import annotations

import random


def should_sample(sample_rate: float) -> bool:
    """Bernoulli sample for sampled-online eval execution."""
    if sample_rate >= 1.0:
        return True
    if sample_rate <= 0.0:
        return False
    return random.random() < sample_rate

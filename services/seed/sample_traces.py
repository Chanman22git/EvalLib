"""Generate simulated traces, eval results, and the injected regression.

The POC seeds the Governance Store's `eval_results` mirror directly (each row
carries a distinct trace_id, standing in for a historical trace). Live Phoenix
traces are produced separately by `demo.sh`. One deliberate regression is
injected: `refund_policy_compliance` on the refund agent drops ~15% from day 5
onward, just after a fake "policy KB re-index" change event.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

random.seed(1742)  # reproducible seed data

# Verdict vocabulary per eval (first entry is the "pass" verdict).
_VERDICTS = {
    "refund_policy_compliance": ("compliant", "ambiguous", "non_compliant"),
    "pii_detection": ("compliant", "ambiguous", "non_compliant"),
    "hallucination_groundedness": ("grounded", "ambiguous", "non_compliant"),
}

_SAMPLE_IO = [
    ("Can I get a refund after 3 weeks?", "Yes, refunds are available within 30 days."),
    ("What is my account email?", "I can't share personal data, but I can help otherwise."),
    ("Summarize the refund policy.", "Refunds within 30 days to the original payment method."),
    ("Is the ebook refundable?", "Digital goods are non-refundable once downloaded."),
]


def _verdict_for_score(score: float, vocab: tuple[str, str, str]) -> str:
    if score >= 0.8:
        return vocab[0]
    if score >= 0.5:
        return vocab[1]
    return vocab[2]


def _score(base: float, jitter: float = 0.08) -> float:
    return round(min(1.0, max(0.0, random.gauss(base, jitter))), 3)


def generate_eval_results(
    *, eval_id: str, agent_id: str, days: int = 7, per_day: int = 6, regression: bool = False
) -> list[dict]:
    """Build eval_result payloads spread over the past `days`."""
    vocab = _VERDICTS.get(eval_id, ("compliant", "ambiguous", "non_compliant"))
    now = datetime.now(timezone.utc)
    results: list[dict] = []
    for day in range(days):
        days_ago = (days - 1) - day  # day=days-1 -> most recent (0 days ago)
        # Healthy baseline ~0.90; injected regression drops to ~0.75 from day 5.
        base = 0.90
        if regression and day >= 5:
            base = 0.75
        for _ in range(per_day):
            # Always in the PAST (>=30 min ago): subtract a within-day offset from
            # the day's anchor so seed rows never future-date and a live question
            # always sorts to the top of the trace list.
            ts = now - timedelta(
                days=days_ago, hours=random.uniform(0.5, 23.5), minutes=random.uniform(0, 59)
            )
            score = _score(base)
            inp, out = random.choice(_SAMPLE_IO)
            results.append(
                {
                    "trace_id": uuid.uuid4().hex,
                    "span_id": uuid.uuid4().hex[:16],
                    "eval_id": eval_id,
                    "eval_version": "1.0.0",
                    "verdict": _verdict_for_score(score, vocab),
                    "score": score,
                    "reasoning": f"[seed] auto-generated verdict for '{inp[:40]}'",
                    "judge_model": "claude-sonnet-4-6",
                    "evaluated_at": ts.isoformat(),
                    "agent_id": agent_id,
                }
            )
    return results


def regression_change_event(agent_id: str, days: int = 7) -> dict:
    """The fake 'policy KB re-index' that precedes the injected regression (day 5)."""
    now = datetime.now(timezone.utc)
    onset = now - timedelta(days=days - 1 - 5)  # start of day 5
    return {
        "event_type": "tool_change",
        "timestamp": onset.isoformat(),
        "agent_id": agent_id,
        "actor": "kb-pipeline",
        "before": {"kb_version": "refund-policy-2024.11", "index": "stable"},
        "after": {"kb_version": "refund-policy-2025.05", "index": "reindexed"},
        "reason": "policy KB re-index",
    }


def routine_change_events(agent_ids: list[str], days: int = 7) -> list[dict]:
    """A handful of benign change events across the week for timeline texture."""
    now = datetime.now(timezone.utc)
    events = []
    samples = [
        ("model_version_change", {"model": "claude-sonnet-4-5"}, {"model": "claude-sonnet-4-6"}, "scheduled model upgrade"),
        ("prompt_change", {"prompt_version": "2"}, {"prompt_version": "3"}, "tightened system prompt"),
        ("routing_change", {"weight": 0.5}, {"weight": 0.8}, "shifted traffic to primary region"),
    ]
    for i, (etype, before, after, reason) in enumerate(samples):
        events.append(
            {
                "event_type": etype,
                "timestamp": (now - timedelta(days=i + 1, hours=2)).isoformat(),
                "agent_id": agent_ids[i % len(agent_ids)],
                "actor": "platform-team",
                "before": before,
                "after": after,
                "reason": reason,
            }
        )
    return events

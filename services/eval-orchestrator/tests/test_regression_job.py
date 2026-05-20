from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src import regression_job
from src.regression_detector import rank_candidate_causes


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_rank_candidate_causes_orders_by_proximity_to_onset():
    onset = datetime(2026, 5, 19, 0, 0, tzinfo=timezone.utc)
    events = [
        {"id": "e1", "event_type": "model_version_change", "reason": "upgrade", "timestamp": _iso(onset - timedelta(hours=10))},
        {"id": "e2", "event_type": "tool_change", "reason": "policy KB re-index", "timestamp": _iso(onset + timedelta(hours=1))},
        {"id": "e3", "event_type": "routing_change", "reason": "traffic shift", "timestamp": _iso(onset - timedelta(hours=30))},
    ]
    causes = rank_candidate_causes(events, onset=onset, top_n=5)
    assert [c["event_id"] for c in causes] == ["e2", "e1", "e3"]
    assert causes[0]["rank"] == 1
    assert causes[0]["reason"] == "policy KB re-index"
    assert causes[0]["proximity_hours"] == 1.0


def test_rank_candidate_causes_skips_unparseable_and_caps_top_n():
    onset = datetime(2026, 5, 19, tzinfo=timezone.utc)
    events = [{"id": f"e{i}", "event_type": "x", "reason": "r", "timestamp": _iso(onset - timedelta(hours=i))} for i in range(8)]
    events.append({"id": "bad", "timestamp": None})
    causes = rank_candidate_causes(events, onset=onset, top_n=5)
    assert len(causes) == 5
    assert "bad" not in [c["event_id"] for c in causes]


class FakeGov:
    """In-memory governance client for the detection job."""

    def __init__(self, *, current, baseline, change_events, existing_alerts=None, approved=True):
        self.current = current
        self.baseline = baseline
        self.change_events = change_events
        self.existing_alerts = existing_alerts or []
        self.approved = approved
        self.created: list[dict] = []

    async def get_agent_mappings(self):
        return [{"eval_id": "pk1", "agent_id": "agent-1", "enabled": True, "sample_rate": 1.0}]

    async def list_evals(self):
        return [
            {
                "id": "pk1",
                "eval_id": "refund_policy_compliance",
                "review_status": "approved" if self.approved else "draft",
            }
        ]

    async def get_eval_results(self, params):
        frm = datetime.fromisoformat(params["from"])
        now = datetime.now(timezone.utc)
        scores = self.current if frm >= now - timedelta(days=2) else self.baseline
        return [{"score": s} for s in scores]

    async def get_regression_alerts(self, params=None):
        return self.existing_alerts

    async def get_change_events(self, params):
        return self.change_events

    async def post_regression_alert(self, payload):
        alert = {**payload, "id": f"alert-{len(self.created)}"}
        self.created.append(alert)
        return alert


@pytest.fixture(autouse=True)
def _no_otel(monkeypatch):
    monkeypatch.setattr(regression_job, "emit_regression_detected", lambda **k: None)


async def test_job_creates_alert_with_top_candidate_cause(monkeypatch):
    now = datetime.now(timezone.utc)
    gov = FakeGov(
        current=[0.74, 0.76, 0.75],   # ~0.75
        baseline=[0.90, 0.91, 0.89],  # ~0.90 → 15pt drop
        change_events=[
            {"id": "kb", "event_type": "tool_change", "reason": "policy KB re-index", "timestamp": (now - timedelta(hours=24)).isoformat()},
            {"id": "mv", "event_type": "model_version_change", "reason": "upgrade", "timestamp": (now - timedelta(hours=40)).isoformat()},
        ],
    )
    result = await regression_job.run_regression_detection(gov)  # type: ignore[arg-type]
    assert result["created"] == 1
    alert = gov.created[0]
    assert alert["eval_id"] == "refund_policy_compliance"
    assert alert["delta"] < -0.10
    assert alert["candidate_causes"][0]["reason"] == "policy KB re-index"


async def test_job_dedupes_existing_open_alert():
    now = datetime.now(timezone.utc)
    gov = FakeGov(
        current=[0.74, 0.76, 0.75],
        baseline=[0.90, 0.91, 0.89],
        change_events=[],
        existing_alerts=[{"eval_id": "refund_policy_compliance", "status": "open"}],
    )
    result = await regression_job.run_regression_detection(gov)  # type: ignore[arg-type]
    assert result["created"] == 0


async def test_job_skips_when_no_regression():
    gov = FakeGov(current=[0.90, 0.91, 0.89], baseline=[0.90, 0.90, 0.91], change_events=[])
    result = await regression_job.run_regression_detection(gov)  # type: ignore[arg-type]
    assert result["created"] == 0


async def test_job_skips_non_approved_eval():
    gov = FakeGov(current=[0.5, 0.5, 0.5], baseline=[0.9, 0.9, 0.9], change_events=[], approved=False)
    result = await regression_job.run_regression_detection(gov)  # type: ignore[arg-type]
    assert result["checked"] == 0
    assert result["created"] == 0

from __future__ import annotations

import uuid

import pytest

from src import suite as suite_mod
from src.executor import Executor
from src.schemas import EvalVerdict, SessionRef, TraceRef

_FAKE_AGENT_ID = str(uuid.uuid4())


def _verdict(eval_id: str, score: float, passed: bool, version: str = "1.0.0") -> EvalVerdict:
    return EvalVerdict(
        trace_id="t1",
        span_id="s1",
        eval_id=eval_id,
        eval_version=version,
        verdict="compliant" if passed else "non_compliant",
        score=score,
        reasoning="test",
        judge_model="claude-test",
        passed=passed,
    )


class FakeGov:
    def __init__(self, evals, scores):
        # evals: list of {id, eval_id, blocking, review_status, ...}
        self._evals = evals
        self._scores = scores  # dict eval_id -> (score, passed)

    async def resolve_agent(self, ref):
        return {"id": _FAKE_AGENT_ID, "name": "a"}

    async def get_agent_mappings(self, agent_id=None):
        return [{"eval_id": e["id"], "agent_id": _FAKE_AGENT_ID, "enabled": True} for e in self._evals]

    async def list_evals(self):
        return self._evals


def _fake_executor_run(scores):
    async def _run(self, eval_def, ref, judge_model=None):
        s, passed = scores[eval_def["eval_id"]]
        return _verdict(eval_def["eval_id"], s, passed)
    return _run


_EVALS = [
    {"id": "pk1", "eval_id": "refund_policy_compliance", "review_status": "approved", "blocking": True},
    {"id": "pk2", "eval_id": "pii_detection",            "review_status": "approved", "blocking": True},
    {"id": "pk3", "eval_id": "response_helpfulness",     "review_status": "approved", "blocking": False},
]


@pytest.fixture()
def trace():
    return TraceRef(trace_id="t1", span_id="s1", input="q", output="a")


async def test_all_pass_high_mean_is_PASS(monkeypatch, trace):
    scores = {"refund_policy_compliance": (0.95, True), "pii_detection": (1.0, True), "response_helpfulness": (0.9, True)}
    monkeypatch.setattr(Executor, "run", _fake_executor_run(scores))
    gov = FakeGov(_EVALS, scores)
    r = await suite_mod.score_trace(agent_ref="a", trace=trace, governance=gov)  # type: ignore[arg-type]
    c = r["consolidated"]
    assert c["status"] == "PASS"
    assert c["pass_count"] == 3 and c["fail_count"] == 0
    assert c["blocking_failures"] == []
    assert c["mean_score"] >= 0.75


async def test_blocking_eval_failure_forces_FAIL(monkeypatch, trace):
    # Mean still high, but one BLOCKING eval failed → FAIL.
    scores = {"refund_policy_compliance": (0.95, True), "pii_detection": (0.95, False), "response_helpfulness": (0.95, True)}
    monkeypatch.setattr(Executor, "run", _fake_executor_run(scores))
    gov = FakeGov(_EVALS, scores)
    r = await suite_mod.score_trace(agent_ref="a", trace=trace, governance=gov)  # type: ignore[arg-type]
    c = r["consolidated"]
    assert c["status"] == "FAIL"
    assert "pii_detection" in c["blocking_failures"]
    assert any("blocking" in reason for reason in c["reasons"])


async def test_low_mean_alone_forces_FAIL(monkeypatch, trace):
    # No blocking failure, but the mean falls below 0.75 → FAIL.
    scores = {"refund_policy_compliance": (0.6, True), "pii_detection": (0.6, True), "response_helpfulness": (0.5, True)}
    monkeypatch.setattr(Executor, "run", _fake_executor_run(scores))
    gov = FakeGov(_EVALS, scores)
    r = await suite_mod.score_trace(agent_ref="a", trace=trace, governance=gov)  # type: ignore[arg-type]
    c = r["consolidated"]
    assert c["status"] == "FAIL"
    assert c["blocking_failures"] == []
    assert any("mean" in reason for reason in c["reasons"])


async def test_non_blocking_failure_does_not_FAIL_when_mean_ok(monkeypatch, trace):
    # A non-blocking eval fails but mean still ≥ 0.75 → PASS.
    scores = {"refund_policy_compliance": (0.95, True), "pii_detection": (0.95, True), "response_helpfulness": (0.4, False)}
    monkeypatch.setattr(Executor, "run", _fake_executor_run(scores))
    gov = FakeGov(_EVALS, scores)
    r = await suite_mod.score_trace(agent_ref="a", trace=trace, governance=gov)  # type: ignore[arg-type]
    c = r["consolidated"]
    assert c["status"] == "PASS"
    assert c["blocking_failures"] == []
    assert c["fail_count"] == 1


# ── Scope split: turn vs session ────────────────────────────────────────────

_MIXED_EVALS = [
    {"id": "pk1", "eval_id": "refund_policy_compliance", "review_status": "approved", "blocking": False, "scope": "turn"},
    {"id": "pk2", "eval_id": "multi_turn_coherence",     "review_status": "approved", "blocking": False, "scope": "session"},
    {"id": "pk3", "eval_id": "resolution",               "review_status": "approved", "blocking": False, "scope": "session"},
]


def _echo_executor_run(scores):
    """Fake Executor.run that echoes the ref so session_id/transcript can be asserted."""
    seen: dict = {}

    async def _run(self, eval_def, ref, judge_model=None):
        seen[eval_def["eval_id"]] = ref
        s, passed = scores[eval_def["eval_id"]]
        return EvalVerdict(
            trace_id=ref.trace_id, span_id=ref.span_id, session_id=ref.session_id,
            eval_id=eval_def["eval_id"], eval_version="1.0.0",
            verdict="compliant" if passed else "non_compliant", score=s,
            reasoning="test", judge_model="claude-test", passed=passed,
        )

    return _run, seen


async def test_score_trace_excludes_session_scoped_evals(monkeypatch, trace):
    scores = {"refund_policy_compliance": (0.9, True), "multi_turn_coherence": (0.9, True), "resolution": (0.9, True)}
    run, _ = _echo_executor_run(scores)
    monkeypatch.setattr(Executor, "run", run)
    gov = FakeGov(_MIXED_EVALS, scores)
    r = await suite_mod.score_trace(agent_ref="a", trace=trace, governance=gov)  # type: ignore[arg-type]
    ran = {v["eval_id"] for v in r["results"]}
    assert ran == {"refund_policy_compliance"}  # only the turn-scoped eval ran


async def test_score_session_runs_only_session_evals_and_stamps_session_id(monkeypatch):
    scores = {"refund_policy_compliance": (0.9, True), "multi_turn_coherence": (0.9, True), "resolution": (0.4, False)}
    run, seen = _echo_executor_run(scores)
    monkeypatch.setattr(Executor, "run", run)
    gov = FakeGov(_MIXED_EVALS, scores)
    session = SessionRef(
        session_id="sess-123",
        turns=[
            TraceRef(trace_id="t1", input="refund after 25 days?", output="Within the 30-day window, yes."),
            TraceRef(trace_id="t2", input="and digital goods?", output="I'll escalate that."),
        ],
    )
    r = await suite_mod.score_session(agent_ref="a", session=session, governance=gov)  # type: ignore[arg-type]

    ran = {v["eval_id"] for v in r["results"]}
    assert ran == {"multi_turn_coherence", "resolution"}  # turn-scoped eval excluded
    assert r["session_id"] == "sess-123"
    assert r["turn_count"] == 2
    # Session verdicts are grouped under the session id (trace_id == session_id).
    assert all(v["session_id"] == "sess-123" and v["trace_id"] == "sess-123" for v in r["results"])
    # resolution failed (0.4) → mean 0.65 < 0.75 → FAIL.
    assert r["consolidated"]["status"] == "FAIL"

    # The judge saw the whole transcript (both turns) as its input.
    transcript = seen["multi_turn_coherence"].input
    assert "refund after 25 days?" in transcript and "and digital goods?" in transcript
    assert transcript.count("[Turn ") == 2

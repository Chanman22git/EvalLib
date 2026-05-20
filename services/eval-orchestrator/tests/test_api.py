from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src import executor as executor_mod
from src.gateway_client import GatewayClient
from src.governance_client import GovernanceClient
from src.main import app

client = TestClient(app)

_APPROVED_EVAL = {
    "eval_id": "refund_policy_compliance",
    "version": "1.0.0",
    "review_status": "approved",
    "criterion_description": "Must comply with refund policy.",
    "prompt_template": "Criterion: {criterion}\nInput: {input}\nOutput: {output}",
    "judge_config": {"model": "claude-sonnet-4-6", "temperature": 0.0},
    "output_schema": {"required": ["verdict", "score"]},
    "retrieval_config": None,
}


@pytest.fixture(autouse=True)
def _patch_clients(monkeypatch):
    async def fake_resolve(self, eval_id, version=None):
        return _APPROVED_EVAL if eval_id == _APPROVED_EVAL["eval_id"] else None

    async def fake_post_result(self, payload):
        return {"id": "stored"}

    async def fake_judge(self, **kwargs):
        return {
            "content": json.dumps(
                {"verdict": "compliant", "score": 0.9, "reasoning": "ok", "passed": True}
            )
        }

    monkeypatch.setattr(GovernanceClient, "resolve_eval", fake_resolve)
    monkeypatch.setattr(GovernanceClient, "post_eval_result", fake_post_result)
    monkeypatch.setattr(GatewayClient, "judge", fake_judge)
    # Keep side effects out of unit tests.
    monkeypatch.setattr(executor_mod, "emit_evaluation_result", lambda *a, **k: None)
    monkeypatch.setattr(executor_mod.phoenix_client, "annotate_span", lambda *a, **k: False)
    monkeypatch.setattr(executor_mod.phoenix_client, "fetch_trace_io", lambda tid: (None, None))


def test_health():
    assert client.get("/health").json()["status"] == "ok"


def test_run_eval_happy_path():
    resp = client.post(
        "/run-eval",
        json={
            "eval_id": "refund_policy_compliance",
            "traces": [
                {"trace_id": "t1", "span_id": "s1", "input": "refund?", "output": "yes 30d"}
            ],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["results"][0]["verdict"] == "compliant"
    assert body["results"][0]["passed"] is True


def test_run_eval_unknown_eval_404():
    resp = client.post("/run-eval", json={"eval_id": "does_not_exist", "traces": []})
    assert resp.status_code == 404


def test_run_eval_rejects_non_approved(monkeypatch):
    async def fake_resolve(self, eval_id, version=None):
        return {**_APPROVED_EVAL, "review_status": "draft"}

    monkeypatch.setattr(GovernanceClient, "resolve_eval", fake_resolve)
    resp = client.post(
        "/run-eval",
        json={"eval_id": "refund_policy_compliance", "traces": [{"trace_id": "t1"}]},
    )
    assert resp.status_code == 400
    assert "not 'approved'" in resp.json()["detail"]


def test_inline_eval_not_implemented():
    resp = client.post("/inline-eval")
    assert resp.status_code == 501

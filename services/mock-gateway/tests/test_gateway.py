from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def _chat_payload(**overrides):
    payload = {
        "messages": [{"role": "user", "content": "What is your refund policy?"}],
        "agent": {
            "agent_id": "agent-support",
            "framework": "langgraph",
            "criticality": "critical",
            "data_classification": "restricted",
            "business_unit": "retail-banking",
        },
    }
    payload.update(overrides)
    return payload


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_chat_happy_path_mock_provider():
    resp = client.post("/v1/chat", json=_chat_payload())
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["content"]
    assert body["usage"]["input_tokens"] > 0
    # Trace + span ids are populated so downstream services can correlate.
    assert len(body["trace_id"]) == 32
    assert len(body["span_id"]) == 16


def test_chat_judge_prompt_returns_json_verdict():
    payload = _chat_payload(
        messages=[
            {"role": "system", "content": "You are a judge. Respond with JSON containing a verdict and score."},
            {"role": "user", "content": "Evaluate this answer."},
        ]
    )
    resp = client.post("/v1/chat", json=payload)
    assert resp.status_code == 200
    parsed = json.loads(resp.json()["content"])
    assert parsed["verdict"] in {"compliant", "non_compliant", "ambiguous"}
    assert 0.0 <= parsed["score"] <= 1.0


def test_chat_rejects_missing_agent_context():
    bad = {"messages": [{"role": "user", "content": "hi"}]}  # no agent block
    resp = client.post("/v1/chat", json=bad)
    assert resp.status_code == 422


def test_change_event_best_effort_when_governance_down():
    resp = client.post(
        "/v1/change-events",
        json={
            "event_type": "prompt_change",
            "agent_id": "agent-support",
            "actor": "tester",
            "before": {"prompt_version": "1"},
            "after": {"prompt_version": "2"},
            "reason": "unit test",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["event_type"] == "prompt_change"
    # Governance API isn't running in unit tests, so forwarding fails gracefully.
    assert body["forwarded"] is False

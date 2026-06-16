from __future__ import annotations

import uuid


def _agent(client, name="agent-x"):
    return client.post("/agents", json={"name": name, "criticality": "high"}).json()


def _eval(client, eval_id="helpfulness"):
    return client.post("/evals", json={"eval_id": eval_id, "version": "1.0.0"}).json()


def test_eval_agent_mapping_happy_and_missing(client):
    agent = _agent(client)
    ev = _eval(client)
    resp = client.post(
        "/eval-agent-mapping",
        json={"eval_id": ev["id"], "agent_id": agent["id"], "sample_rate": 0.5},
    )
    assert resp.status_code == 201
    assert resp.json()["sample_rate"] == 0.5

    listed = client.get("/eval-agent-mapping", params={"agent_id": agent["id"]})
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    # missing eval → 404
    bad = client.post(
        "/eval-agent-mapping",
        json={"eval_id": str(uuid.uuid4()), "agent_id": agent["id"]},
    )
    assert bad.status_code == 404


def test_change_events_ingest_and_query(client):
    resp = client.post(
        "/change-events",
        json={
            "event_type": "prompt_change",
            "actor": "gateway",
            "before": {"v": 1},
            "after": {"v": 2},
            "reason": "tuned prompt",
        },
    )
    assert resp.status_code == 201
    q = client.get("/change-events", params={"event_type": "prompt_change"})
    assert q.status_code == 200
    assert len(q.json()) == 1


def test_eval_results_create_query_aggregate(client):
    agent = _agent(client)
    for verdict, score in [("compliant", 0.9), ("non_compliant", 0.2), ("compliant", 0.8)]:
        r = client.post(
            "/eval-results",
            json={
                "trace_id": "trace-1",
                "eval_id": "refund_policy_compliance",
                "verdict": verdict,
                "score": score,
                "agent_id": agent["id"],
            },
        )
        assert r.status_code == 201

    by_trace = client.get("/eval-results", params={"trace_id": "trace-1"})
    assert len(by_trace.json()) == 3

    agg = client.get("/eval-results/aggregate", params={"agent_id": agent["id"]})
    assert agg.status_code == 200
    row = agg.json()[0]
    assert row["count"] == 3
    assert row["pass_rate"] == round(2 / 3, 4)


def test_regression_alert_lifecycle(client):
    agent = _agent(client)
    created = client.post(
        "/regression-alerts",
        json={
            "agent_id": agent["id"],
            "eval_id": "refund_policy_compliance",
            "baseline_score": 0.9,
            "current_score": 0.75,
            "delta": -0.15,
            "candidate_causes": [{"event_type": "prompt_change", "rank": 1}],
        },
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    updated = client.patch(f"/regression-alerts/{alert_id}", json={"status": "investigating"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "investigating"


def test_calibration_set_missing_404(client):
    resp = client.get(f"/calibration-sets/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_create_eval_with_agent_ids_auto_creates_mappings(client):
    agent = client.post("/agents", json={"name": "a-suite", "criticality": "low"}).json()
    resp = client.post(
        "/evals",
        json={
            "eval_id": "attached_demo",
            "version": "1.0.0",
            "blocking": True,
            "agent_ids": [agent["id"]],
        },
    )
    assert resp.status_code == 201
    ev = resp.json()
    assert ev["blocking"] is True
    mappings = client.get("/eval-agent-mapping", params={"eval_id": ev["id"]}).json()
    assert len(mappings) == 1
    assert mappings[0]["agent_id"] == agent["id"]


def test_eval_scope_defaults_to_turn_and_round_trips(client):
    # Default scope is "turn".
    default = client.post("/evals", json={"eval_id": "turn_default", "version": "1.0.0"}).json()
    assert default["scope"] == "turn"

    # Explicit session scope round-trips on read.
    session = client.post(
        "/evals",
        json={"eval_id": "coherence_demo", "version": "1.0.0", "scope": "session"},
    ).json()
    assert session["scope"] == "session"
    fetched = client.get(f"/evals/{session['id']}").json()
    assert fetched["scope"] == "session"


def test_eval_result_session_id_round_trips_and_filters(client):
    agent = _agent(client)
    # One session-scoped row (trace_id == session_id) + two turn rows on the same session.
    rows = [
        {"trace_id": "sess-1", "session_id": "sess-1", "eval_id": "multi_turn_coherence"},
        {"trace_id": "turn-a", "session_id": "sess-1", "eval_id": "refund_policy_compliance"},
        {"trace_id": "turn-b", "session_id": "sess-1", "eval_id": "refund_policy_compliance"},
        {"trace_id": "turn-c", "session_id": "sess-2", "eval_id": "refund_policy_compliance"},
    ]
    for row in rows:
        r = client.post(
            "/eval-results",
            json={**row, "verdict": "compliant", "score": 0.9, "agent_id": agent["id"]},
        )
        assert r.status_code == 201
        assert r.json()["session_id"] == row["session_id"]

    by_session = client.get("/eval-results", params={"session_id": "sess-1"}).json()
    assert len(by_session) == 3
    assert {r["trace_id"] for r in by_session} == {"sess-1", "turn-a", "turn-b"}


def test_create_eval_with_unknown_agent_id_404(client):
    resp = client.post(
        "/evals",
        json={"eval_id": "bad_attach", "agent_ids": [str(uuid.uuid4())]},
    )
    assert resp.status_code == 404


def test_eval_result_with_unknown_agent_id_is_stored_unattributed(client):
    # A stale agent_id (e.g. after a reseed) must not drop the eval result.
    resp = client.post(
        "/eval-results",
        json={
            "trace_id": "trace-stale",
            "eval_id": "refund_policy_compliance",
            "verdict": "compliant",
            "score": 0.9,
            "agent_id": str(uuid.uuid4()),  # does not exist
        },
    )
    assert resp.status_code == 201
    assert resp.json()["agent_id"] is None

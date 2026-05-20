from __future__ import annotations


def _agent_body(**overrides):
    body = {
        "name": "refund-agent",
        "framework": "langgraph",
        "criticality": "critical",
        "data_classification": "restricted",
        "business_unit": "retail-banking",
        "owner_email": "owner@example.com",
    }
    body.update(overrides)
    return body


def test_create_and_get_agent(client):
    resp = client.post("/agents", json=_agent_body())
    assert resp.status_code == 201
    agent = resp.json()
    assert agent["name"] == "refund-agent"
    assert agent["status"] == "active"

    got = client.get(f"/agents/{agent['id']}")
    assert got.status_code == 200
    assert got.json()["criticality"] == "critical"


def test_duplicate_agent_name_conflicts(client):
    assert client.post("/agents", json=_agent_body()).status_code == 201
    dup = client.post("/agents", json=_agent_body())
    assert dup.status_code == 409


def test_get_missing_agent_404(client):
    import uuid

    resp = client.get(f"/agents/{uuid.uuid4()}")
    assert resp.status_code == 404


def test_filter_agents_by_criticality(client):
    client.post("/agents", json=_agent_body(name="a-critical", criticality="critical"))
    client.post("/agents", json=_agent_body(name="b-low", criticality="low"))
    resp = client.get("/agents", params={"criticality": "low"})
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()]
    assert names == ["b-low"]


def test_retire_agent_soft_deletes(client):
    agent = client.post("/agents", json=_agent_body()).json()
    resp = client.delete(f"/agents/{agent['id']}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "retired"


def test_audit_log_records_agent_registration(client):
    agent = client.post("/agents", json=_agent_body()).json()
    log = client.get("/audit-log", params={"entity_type": "agent", "entity_id": agent["id"]})
    assert log.status_code == 200
    actions = [e["action"] for e in log.json()]
    assert "agent.register" in actions

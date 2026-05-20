from __future__ import annotations


def _create_eval(client, **overrides):
    body = {
        "eval_id": "refund_policy_compliance",
        "version": "1.0.0",
        "criterion_description": "Response must comply with the documented refund policy.",
        "evaluator_type": "llm_as_judge",
        "prompt_template": "Judge: {input} / {output}. Return JSON with verdict and score.",
        "agreement_threshold": 0.75,
        "owner_email": "owner@example.com",
    }
    body.update(overrides)
    return client.post("/evals", json=body)


def _calibration_set(client, agreement: float, name: str):
    return client.post(
        "/calibration-sets",
        json={
            "name": name,
            "examples": [
                {
                    "input": "Can I get a refund?",
                    "output": "Yes within 30 days.",
                    "human_verdict": "compliant",
                    "rater_count": 3,
                    "agreement": agreement,
                }
            ],
        },
    ).json()


def test_eval_created_as_draft(client):
    resp = _create_eval(client)
    assert resp.status_code == 201
    assert resp.json()["review_status"] == "draft"


def test_duplicate_eval_id_version_conflicts(client):
    assert _create_eval(client).status_code == 201
    assert _create_eval(client).status_code == 409


def test_cannot_approve_from_draft(client):
    ev = _create_eval(client).json()
    resp = client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "a@b.com"})
    assert resp.status_code == 400
    assert "Illegal transition" in resp.json()["detail"]


def test_full_approval_flow_with_calibration_gate(client):
    ev = _create_eval(client).json()

    # draft → in_review
    r = client.post(f"/evals/{ev['id']}/submit-for-review", json={"actor": "tester"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "in_review"

    # approve fails: no calibration set attached
    r = client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "appr@b.com"})
    assert r.status_code == 400
    assert "calibration" in r.json()["detail"].lower()

    # attach a weak calibration set (agreement 0.50 < threshold 0.75)
    weak = _calibration_set(client, 0.50, "weak-set")
    r = client.post(f"/evals/{ev['id']}/calibration", json={"calibration_set_id": weak["id"]})
    assert r.status_code == 200
    assert r.json()["last_judge_human_agreement"] == 0.5

    # approve still fails: agreement below threshold (AC-9)
    r = client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "appr@b.com"})
    assert r.status_code == 400
    assert "threshold" in r.json()["detail"].lower()

    # attach a stronger calibration set (agreement 0.90)
    strong = _calibration_set(client, 0.90, "strong-set")
    r = client.post(f"/evals/{ev['id']}/calibration", json={"calibration_set_id": strong["id"]})
    assert r.json()["last_judge_human_agreement"] == 0.9

    # approval now succeeds
    r = client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "appr@b.com"})
    assert r.status_code == 200
    assert r.json()["review_status"] == "approved"
    assert r.json()["approver_email"] == "appr@b.com"
    assert r.json()["approved_at"] is not None

    # audit log shows every transition (AC-5)
    log = client.get("/audit-log", params={"entity_type": "eval", "entity_id": ev["id"]}).json()
    actions = {e["action"] for e in log}
    assert {"eval.create", "eval.in_review", "eval.calibration", "eval.approved"} <= actions


def test_approved_eval_is_immutable(client):
    ev = _create_eval(client).json()
    client.post(f"/evals/{ev['id']}/submit-for-review", json={})
    strong = _calibration_set(client, 0.9, "s")
    client.post(f"/evals/{ev['id']}/calibration", json={"calibration_set_id": strong["id"]})
    client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "a@b.com"})

    # editing an approved eval is rejected
    r = client.patch(f"/evals/{ev['id']}", json={"criterion_description": "changed"})
    assert r.status_code == 400
    assert "immutable" in r.json()["detail"].lower()


def test_deprecate_after_approval(client):
    ev = _create_eval(client).json()
    client.post(f"/evals/{ev['id']}/submit-for-review", json={})
    strong = _calibration_set(client, 0.9, "s")
    client.post(f"/evals/{ev['id']}/calibration", json={"calibration_set_id": strong["id"]})
    client.post(f"/evals/{ev['id']}/approve", json={"approver_email": "a@b.com"})
    r = client.post(f"/evals/{ev['id']}/deprecate", json={})
    assert r.status_code == 200
    assert r.json()["review_status"] == "deprecated"

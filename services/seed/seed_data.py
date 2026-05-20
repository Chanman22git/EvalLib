"""Populate the Governance Store with realistic POC data (FR-SD-1).

Idempotency: this script assumes a fresh store (`make reset` first). It talks to
the Governance API over HTTP rather than the DB directly, so it also exercises
the API surface end-to-end.

Seeds: 5 agents, 8 evals (mixed governance states), 3 calibration sets, ~290
eval results across 7 days, benign change events, one injected refund-policy
regression (+ its 'policy KB re-index' change event and a regression alert).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import httpx
import yaml

from sample_traces import (
    generate_eval_results,
    regression_change_event,
    routine_change_events,
)

BASE_URL = os.getenv("GOVERNANCE_API_URL", "http://governance-api:8001").rstrip("/")
HERE = Path(__file__).parent

AGENTS = [
    {
        "name": "customer-support-refund",
        "description": "Handles customer refund requests end to end.",
        "framework": "langgraph",
        "criticality": "critical",
        "data_classification": "restricted",
        "business_unit": "retail-banking",
        "owner_team": "customer-support",
        "owner_email": "cs-owner@example.com",
        "is_third_party": False,
    },
    {
        "name": "internal-knowledge-assistant",
        "description": "Answers employee questions from internal docs.",
        "framework": "custom",
        "criticality": "medium",
        "data_classification": "internal",
        "business_unit": "operations",
        "owner_team": "ml-platform",
        "owner_email": "mlp-owner@example.com",
        "is_third_party": False,
    },
    {
        "name": "code-review-agent",
        "description": "Reviews pull requests for style and bugs.",
        "framework": "crewai",
        "criticality": "low",
        "data_classification": "internal",
        "business_unit": "engineering",
        "owner_team": "developer-experience",
        "owner_email": "dx-owner@example.com",
        "is_third_party": False,
    },
    {
        "name": "vendor-claims-agent",
        "description": "Third-party agent that triages insurance claims.",
        "framework": "vendor",
        "criticality": "high",
        "data_classification": "confidential",
        "business_unit": "insurance",
        "owner_team": "claims",
        "owner_email": "claims-owner@example.com",
        "is_third_party": True,
    },
    {
        "name": "marketing-copy-generator",
        "description": "Generates marketing copy for campaigns.",
        "framework": "custom",
        "criticality": "low",
        "data_classification": "public",
        "business_unit": "marketing",
        "owner_team": "marketing",
        "owner_email": "mktg-owner@example.com",
        "is_third_party": False,
    },
]

# (eval_id, agent_name, sample_rate) — only approved evals are mapped.
MAPPINGS = [
    ("refund_policy_compliance", "customer-support-refund", 0.5),
    ("pii_detection", "customer-support-refund", 0.25),
    ("pii_detection", "internal-knowledge-assistant", 0.25),
    ("hallucination_groundedness", "internal-knowledge-assistant", 0.2),
    ("hallucination_groundedness", "code-review-agent", 0.2),
    ("pii_detection", "vendor-claims-agent", 0.25),
    ("pii_detection", "marketing-copy-generator", 0.25),
]


def wait_for_api(client: httpx.Client, retries: int = 30) -> None:
    for _ in range(retries):
        try:
            if client.get(f"{BASE_URL}/health").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(2)
    sys.exit(f"Governance API at {BASE_URL} never became healthy.")


def load_yaml(name: str):
    return yaml.safe_load((HERE / "sample_evals" / name).read_text())


def seed() -> None:
    with httpx.Client(timeout=30.0) as client:
        wait_for_api(client)

        # 1. Agents
        agent_ids: dict[str, str] = {}
        for a in AGENTS:
            r = client.post(f"{BASE_URL}/agents", json=a)
            r.raise_for_status()
            agent_ids[a["name"]] = r.json()["id"]
        print(f"Seeded {len(agent_ids)} agents.")

        # 2. Calibration sets
        cal_ids: dict[str, str] = {}
        for c in load_yaml("calibration_sets.yaml"):
            key = c.pop("key")
            r = client.post(f"{BASE_URL}/calibration-sets", json=c)
            r.raise_for_status()
            cal_ids[key] = r.json()["id"]
        print(f"Seeded {len(cal_ids)} calibration sets.")

        # 3. Evals (+ drive the governance state machine)
        eval_pks: dict[str, str] = {}
        for spec in load_yaml("evals.yaml"):
            calibration = spec.pop("calibration", None)
            target = spec.pop("target_status", "draft")
            approver = spec.pop("approver_email", "approver@example.com")
            r = client.post(f"{BASE_URL}/evals", json=spec)
            r.raise_for_status()
            ev = r.json()
            eval_pks[spec["eval_id"]] = ev["id"]
            pk = ev["id"]

            if target in ("in_review", "approved"):
                client.post(f"{BASE_URL}/evals/{pk}/submit-for-review", json={"actor": "seed"}).raise_for_status()
            if target == "approved":
                if calibration:
                    client.post(
                        f"{BASE_URL}/evals/{pk}/calibration",
                        json={"calibration_set_id": cal_ids[calibration], "actor": "seed"},
                    ).raise_for_status()
                client.post(
                    f"{BASE_URL}/evals/{pk}/approve",
                    json={"approver_email": approver, "actor": "seed"},
                ).raise_for_status()
        print(f"Seeded {len(eval_pks)} evals.")

        # 4. Eval-agent mappings
        for eval_id, agent_name, rate in MAPPINGS:
            client.post(
                f"{BASE_URL}/eval-agent-mapping",
                json={
                    "eval_id": eval_pks[eval_id],
                    "agent_id": agent_ids[agent_name],
                    "sample_rate": rate,
                },
            ).raise_for_status()
        print(f"Seeded {len(MAPPINGS)} eval-agent mappings.")

        # 5. Eval results across 7 days (+ injected regression on refund agent)
        total_results = 0
        for eval_id, agent_name, _ in MAPPINGS:
            regression = eval_id == "refund_policy_compliance" and agent_name == "customer-support-refund"
            for payload in generate_eval_results(
                eval_id=eval_id, agent_id=agent_ids[agent_name], regression=regression
            ):
                client.post(f"{BASE_URL}/eval-results", json=payload).raise_for_status()
                total_results += 1
        print(f"Seeded {total_results} eval results.")

        # 6. Change events (benign texture + the KB re-index that precedes the regression)
        refund_agent = agent_ids["customer-support-refund"]
        for ev in routine_change_events(list(agent_ids.values())):
            client.post(f"{BASE_URL}/change-events", json=ev).raise_for_status()
        client.post(f"{BASE_URL}/change-events", json=regression_change_event(refund_agent)).raise_for_status()
        print("Seeded change events (incl. policy KB re-index).")

        # 7. Regression alert (groundwork for AC-7; Phase F also detects this live)
        client.post(
            f"{BASE_URL}/regression-alerts",
            json={
                "agent_id": refund_agent,
                "eval_id": "refund_policy_compliance",
                "baseline_score": 0.90,
                "current_score": 0.75,
                "delta": -0.15,
                "candidate_causes": [
                    {
                        "rank": 1,
                        "event_type": "tool_change",
                        "reason": "policy KB re-index",
                        "proximity_hours": 2,
                    },
                    {"rank": 2, "event_type": "model_version_change", "reason": "scheduled model upgrade"},
                ],
            },
        ).raise_for_status()
        print("Seeded 1 injected regression alert.")

    print("\nSeed complete. Open the UI (:3000), Phoenix (:6006), or :8001/docs.")


if __name__ == "__main__":
    seed()

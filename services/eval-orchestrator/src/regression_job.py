"""Periodic regression-detection job (FR-RD-1..3).

For each approved (agent, eval) pair, compare the current rolling window's mean
score against an older baseline window. When a regression triggers, run a
candidate-cause analysis over the agent's recent change events, persist a
regression alert (deduped against existing open alerts), and emit an
`enterprise.regression.detected` OTel event.

The detection math (`is_regression`) and cause ranking (`rank_candidate_causes`)
live in `regression_detector` so they can be unit-tested in isolation.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from statistics import mean

from .config import settings
from .governance_client import GovernanceClient
from .otel_emitter import emit_regression_detected
from .regression_detector import is_regression, rank_candidate_causes

logger = logging.getLogger("eval-orchestrator.regression")


async def run_regression_detection(governance: GovernanceClient | None = None) -> dict:
    governance = governance or GovernanceClient()

    mappings = await governance.get_agent_mappings()
    evals = await governance.list_evals()
    eval_by_pk = {e["id"]: e for e in evals}

    now = datetime.now(timezone.utc)
    current_start = now - timedelta(hours=settings.regression_current_window_hours)
    baseline_start = now - timedelta(days=settings.regression_baseline_lookback_days)
    baseline_end = now - timedelta(days=settings.regression_baseline_recent_cutoff_days)

    checked = 0
    created: list[dict] = []

    for m in mappings:
        if not m.get("enabled", True):
            continue
        ev = eval_by_pk.get(m["eval_id"])
        if not ev or ev["review_status"] != "approved":
            continue

        agent_id = m["agent_id"]
        eval_id = ev["eval_id"]
        checked += 1

        current = await governance.get_eval_results(
            {
                "agent_id": agent_id,
                "eval_id": eval_id,
                "from": current_start.isoformat(),
                "to": now.isoformat(),
                "limit": 2000,
            }
        )
        baseline = await governance.get_eval_results(
            {
                "agent_id": agent_id,
                "eval_id": eval_id,
                "from": baseline_start.isoformat(),
                "to": baseline_end.isoformat(),
                "limit": 2000,
            }
        )

        cur_scores = [r["score"] for r in current]
        base_scores = [r["score"] for r in baseline]
        if len(cur_scores) < settings.regression_min_samples or len(base_scores) < settings.regression_min_samples:
            continue

        regressed, delta = is_regression(base_scores, cur_scores)
        if not regressed:
            continue

        # Dedupe: skip if an open alert already exists for this (agent, eval).
        existing = await governance.get_regression_alerts({"agent_id": agent_id, "status": "open"})
        if any(a["eval_id"] == eval_id for a in existing):
            logger.info("Open alert already exists for %s/%s; skipping.", agent_id, eval_id)
            continue

        # Candidate causes: agent's change events in the 48h window before now,
        # ranked by proximity to the regression onset (the current window start).
        cause_window_start = now - timedelta(hours=48)
        change_events = await governance.get_change_events(
            {
                "agent_id": agent_id,
                "from": cause_window_start.isoformat(),
                "to": now.isoformat(),
                "limit": 200,
            }
        )
        causes = rank_candidate_causes(change_events, onset=current_start, top_n=5)

        baseline_score = round(mean(base_scores), 4)
        current_score = round(mean(cur_scores), 4)
        alert = await governance.post_regression_alert(
            {
                "agent_id": agent_id,
                "eval_id": eval_id,
                "baseline_score": baseline_score,
                "current_score": current_score,
                "delta": delta,
                "candidate_causes": causes,
            }
        )
        emit_regression_detected(
            agent_id=agent_id,
            eval_id=eval_id,
            baseline_score=baseline_score,
            current_score=current_score,
            delta=delta,
            candidate_causes=causes,
        )
        created.append(alert)
        logger.info("Regression detected: %s/%s delta=%s", agent_id, eval_id, delta)

    return {"checked": checked, "created": len(created), "alerts": created}


async def regression_loop() -> None:
    logger.info(
        "Regression detection worker started (interval=%ss)", settings.regression_interval_seconds
    )
    while True:
        try:
            await run_regression_detection()
        except Exception as exc:  # noqa: BLE001 — never let the loop die
            logger.warning("Regression detection pass error: %s", exc)
        await asyncio.sleep(settings.regression_interval_seconds)

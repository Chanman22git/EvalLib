"""Run an agent's full eval suite on a single trace and consolidate the verdicts.

Resolves the agent → its enabled+approved mapped evals → runs them in parallel
via the existing executor → returns per-eval verdicts plus a consolidated block.

Consolidation (user spec):
    status = PASS  iff  mean(scores) >= threshold  AND  no blocking eval failed.
"""

from __future__ import annotations

import asyncio
from statistics import mean

from .config import settings
from .executor import EvalNotRunnable, Executor
from .governance_client import GovernanceClient
from .schemas import EvalVerdict, TraceRef


async def score_trace(
    *,
    agent_ref: str,
    trace: TraceRef,
    eval_ids: list[str] | None = None,
    governance: GovernanceClient | None = None,
) -> dict:
    governance = governance or GovernanceClient()
    agent = await governance.resolve_agent(agent_ref)
    if agent is None:
        raise LookupError(f"Agent '{agent_ref}' not found")
    agent_id = agent["id"]
    # Don't mutate the caller's TraceRef. Stamp agent_id on a fresh copy each run.
    trace_template = trace.model_copy(update={"agent_id": agent_id})

    # Pick the suite: enabled+approved evals mapped to the agent (or explicit subset).
    mappings = await governance.get_agent_mappings(agent_id=agent_id)
    all_evals = await governance.list_evals()
    eval_by_pk = {e["id"]: e for e in all_evals}

    suite: list[dict] = []
    for m in mappings:
        if not m.get("enabled", True):
            continue
        ev = eval_by_pk.get(m["eval_id"])
        if not ev or ev["review_status"] != "approved":
            continue
        if eval_ids and ev["eval_id"] not in eval_ids:
            continue
        suite.append(ev)

    executor = Executor(governance=governance)

    async def _run(ev: dict) -> tuple[dict, EvalVerdict | None, str | None]:
        try:
            return ev, await executor.run(ev, trace_template.model_copy()), None
        except EvalNotRunnable as exc:
            return ev, None, str(exc)
        except Exception as exc:  # noqa: BLE001 — surface as a skipped eval
            return ev, None, f"run failed: {exc}"

    paired = await asyncio.gather(*(_run(ev) for ev in suite))

    results: list[EvalVerdict] = []
    blocking_failures: list[str] = []
    pass_count = 0
    fail_count = 0
    scores: list[float] = []

    for ev, verdict, err in paired:
        if verdict is None:
            # Skipped (not runnable) — does not contribute to the score.
            continue
        results.append(verdict)
        scores.append(verdict.score)
        if verdict.passed:
            pass_count += 1
        else:
            fail_count += 1
            if ev.get("blocking"):
                blocking_failures.append(verdict.eval_id)

    threshold = settings.suite_pass_threshold
    mean_score = round(mean(scores), 4) if scores else 0.0
    reasons: list[str] = []
    if not scores:
        reasons.append("no approved+mapped evals to score")
    if scores and mean_score < threshold:
        reasons.append(f"mean {mean_score:.2f} below threshold {threshold:.2f}")
    if blocking_failures:
        reasons.append(f"blocking eval(s) failed: {', '.join(blocking_failures)}")
    status = "PASS" if (scores and mean_score >= threshold and not blocking_failures) else "FAIL"

    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "trace_id": trace.trace_id,
        "results": [v.model_dump() for v in results],
        "consolidated": {
            "status": status,
            "mean_score": mean_score,
            "threshold": threshold,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "blocking_failures": blocking_failures,
            "reasons": reasons,
        },
    }

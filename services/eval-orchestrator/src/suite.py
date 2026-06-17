"""Run an agent's eval suite and consolidate the verdicts.

`score_trace` runs the agent's **turn-scoped** evals against one trace.
`score_session` runs its **session-scoped** evals against a whole conversation
transcript. Both resolve the agent → its enabled+approved mapped evals → run
them in parallel via the existing executor → return per-eval verdicts plus a
consolidated block.

Consolidation (user spec):
    status = PASS  iff  mean(scores) >= threshold  AND  no blocking eval failed.
"""

from __future__ import annotations

import asyncio
from statistics import mean

from .config import settings
from .executor import EvalNotRunnable, Executor
from .governance_client import GovernanceClient
from .schemas import EvalVerdict, SessionRef, TraceRef


async def _resolve_suite(
    governance: GovernanceClient,
    agent_id: str,
    *,
    scope: str,
    eval_ids: list[str] | None,
) -> list[dict]:
    """Enabled + approved evals mapped to the agent, filtered to one scope."""
    mappings = await governance.get_agent_mappings(agent_id=agent_id)
    eval_by_pk = {e["id"]: e for e in await governance.list_evals()}

    suite: list[dict] = []
    for m in mappings:
        if not m.get("enabled", True):
            continue
        ev = eval_by_pk.get(m["eval_id"])
        if not ev or ev["review_status"] != "approved":
            continue
        if ev.get("scope", "turn") != scope:
            continue
        if eval_ids and ev["eval_id"] not in eval_ids:
            continue
        suite.append(ev)
    return suite


async def _run_and_consolidate(
    executor: Executor, suite: list[dict], ref: TraceRef
) -> tuple[list[EvalVerdict], dict]:
    """Run every eval in `suite` against `ref` and build the consolidated block."""

    async def _run(ev: dict) -> tuple[dict, EvalVerdict | None, str | None]:
        try:
            return ev, await executor.run(ev, ref.model_copy()), None
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

    for ev, verdict, _err in paired:
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

    consolidated = {
        "status": status,
        "mean_score": mean_score,
        "threshold": threshold,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "blocking_failures": blocking_failures,
        "reasons": reasons,
    }
    return results, consolidated


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

    suite = await _resolve_suite(governance, agent_id, scope="turn", eval_ids=eval_ids)
    # Don't mutate the caller's TraceRef. Stamp agent_id on a fresh copy each run.
    trace_template = trace.model_copy(update={"agent_id": agent_id})
    executor = Executor(governance=governance)
    results, consolidated = await _run_and_consolidate(executor, suite, trace_template)

    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "trace_id": trace.trace_id,
        "results": [v.model_dump() for v in results],
        "consolidated": consolidated,
    }


def _build_transcript(turns: list[TraceRef]) -> str:
    """Render an ordered list of turns into a readable conversation transcript."""
    lines: list[str] = []
    for i, t in enumerate(turns, start=1):
        lines.append(f"[Turn {i}]")
        lines.append(f"User: {(t.input or '').strip()}")
        lines.append(f"Agent: {(t.output or '').strip()}")
    return "\n".join(lines)


async def score_session(
    *,
    agent_ref: str,
    session: SessionRef,
    eval_ids: list[str] | None = None,
    governance: GovernanceClient | None = None,
) -> dict:
    governance = governance or GovernanceClient()
    agent = await governance.resolve_agent(agent_ref)
    if agent is None:
        raise LookupError(f"Agent '{agent_ref}' not found")
    agent_id = agent["id"]

    suite = await _resolve_suite(governance, agent_id, scope="session", eval_ids=eval_ids)

    # Collapse the conversation into one synthetic trace the judge can read:
    #   input  = full transcript, output = the final agent turn.
    # trace_id = session_id so persisted session verdicts group with the thread.
    transcript = _build_transcript(session.turns)
    final_output = session.turns[-1].output if session.turns else ""
    session_trace = TraceRef(
        trace_id=session.session_id,
        session_id=session.session_id,
        input=transcript,
        output=final_output,
        agent_id=agent_id,
    )
    executor = Executor(governance=governance)
    results, consolidated = await _run_and_consolidate(executor, suite, session_trace)

    return {
        "agent_id": agent_id,
        "agent_name": agent.get("name"),
        "session_id": session.session_id,
        "turn_count": len(session.turns),
        "results": [v.model_dump() for v in results],
        "consolidated": consolidated,
    }

"""Sampled-online execution (FR-EO-4).

A background loop periodically samples recent traces per the eval-agent mapping's
`sample_rate` and runs the applicable approved evals. Trace discovery uses the
Phoenix client and is best-effort: when Phoenix returns nothing the pass is a
no-op. The core pass is also exposed via `POST /sample-once` for the demo + tests.
"""

from __future__ import annotations

import asyncio
import logging

from . import phoenix_client
from .config import settings
from .executor import EvalNotRunnable, Executor
from .governance_client import GovernanceClient
from .samplers import should_sample
from .schemas import EvalVerdict, SampleRunResponse, TraceRef

logger = logging.getLogger("eval-orchestrator.worker")


async def run_sampling_pass(governance: GovernanceClient | None = None) -> SampleRunResponse:
    governance = governance or GovernanceClient()
    executor = Executor(governance=governance)

    mappings = await governance.get_agent_mappings()
    enabled = [m for m in mappings if m.get("enabled", True)]

    sampled = 0
    results: list[EvalVerdict] = []
    for mapping in enabled:
        eval_def = await governance.get_eval_by_pk(mapping["eval_id"])
        if eval_def["review_status"] != "approved":
            continue
        agent_id = mapping["agent_id"]
        recent = phoenix_client_recent_traces(agent_id)
        for ref in recent:
            if not should_sample(mapping.get("sample_rate", 1.0)):
                continue
            sampled += 1
            ref.agent_id = agent_id  # type: ignore[assignment]
            try:
                results.append(await executor.run(eval_def, ref))
            except EvalNotRunnable as exc:
                logger.info("Skipping eval: %s", exc)
    return SampleRunResponse(sampled=sampled, evaluated=len(results), results=results)


def phoenix_client_recent_traces(agent_id: str) -> list[TraceRef]:
    """Best-effort discovery of recent traces for an agent from Phoenix."""
    client = phoenix_client._client()  # noqa: SLF001 — internal helper reuse
    if client is None:
        return []
    try:
        spans = client.spans.get_spans(
            project_identifier=settings.phoenix_project,
            attributes={"enterprise.agent.id": agent_id},
            limit=25,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Phoenix trace discovery failed for agent %s: %s", agent_id, exc)
        return []
    refs: list[TraceRef] = []
    for span in spans:
        if not isinstance(span, dict):
            continue
        refs.append(
            TraceRef(
                trace_id=str(span.get("context", {}).get("trace_id", "")),
                span_id=str(span.get("context", {}).get("span_id", "")) or None,
            )
        )
    return [r for r in refs if r.trace_id]


async def sampling_loop() -> None:
    logger.info("Sampled-online worker started (interval=%ss)", settings.sampling_interval_seconds)
    while True:
        try:
            await run_sampling_pass()
        except Exception as exc:  # noqa: BLE001 — never let the loop die
            logger.warning("Sampling pass error: %s", exc)
        await asyncio.sleep(settings.sampling_interval_seconds)

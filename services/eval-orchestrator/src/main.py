from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .config import settings
from .executor import EvalNotRunnable, Executor
from .governance_client import GovernanceClient
from .otel_emitter import init_tracing
from .schemas import RunEvalRequest, RunEvalResponse, SampleRunResponse
from .worker import run_sampling_pass, sampling_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing(app)
    task: asyncio.Task | None = None
    if settings.sampling_enabled:
        task = asyncio.create_task(sampling_loop())
    try:
        yield
    finally:
        if task is not None:
            task.cancel()


app = FastAPI(
    title="EvalLib Eval Orchestrator",
    description="Runs evals on traces (offline + sampled-online) and emits OTel eval events.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "eval-orchestrator"}


@app.post("/run-eval", response_model=RunEvalResponse)
async def run_eval(req: RunEvalRequest) -> RunEvalResponse:
    """Offline mode: run one eval synchronously over a list of traces (FR-EO-4)."""
    governance = GovernanceClient()
    eval_def = await governance.resolve_eval(req.eval_id, req.version)
    if eval_def is None:
        raise HTTPException(status_code=404, detail=f"Eval '{req.eval_id}' not found")

    executor = Executor(governance=governance)
    results = []
    for ref in req.traces:
        try:
            results.append(await executor.run(eval_def, ref, judge_model=req.judge_model))
        except EvalNotRunnable as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    return RunEvalResponse(
        eval_id=eval_def["eval_id"],
        eval_version=eval_def["version"],
        count=len(results),
        results=results,
    )


@app.post("/sample-once", response_model=SampleRunResponse)
async def sample_once() -> SampleRunResponse:
    """Trigger a single sampled-online pass on demand (used by the demo + tests)."""
    return await run_sampling_pass()


@app.post("/inline-eval", status_code=501)
async def inline_eval() -> dict:
    """Inline (synchronous gateway-gating) mode — scaffolded only (FR-EO-4)."""
    raise HTTPException(
        status_code=501,
        detail=(
            "Inline eval gating is Phase 2 and not implemented in the POC. "
            "The gateway scaffolds for it but does not block or rewrite responses."
        ),
    )

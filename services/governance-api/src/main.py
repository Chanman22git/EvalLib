from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import Base, engine
from .otel import init_tracing
from .routers import (
    agents,
    audit_log,
    calibration_sets,
    change_events,
    eval_agent_mapping,
    eval_results,
    evals,
    regression_alerts,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In real deployments Alembic owns the schema; for the POC we also create
    # tables on boot so `docker compose up` is enough. Skipped under pytest
    # (the test fixture manages its own schema).
    if settings.auto_create_tables and not os.getenv("PYTEST_CURRENT_TEST"):
        Base.metadata.create_all(bind=engine)
    init_tracing(app)
    yield


app = FastAPI(
    title="EvalLib Governance API",
    description="Agent + eval registry, governance state machine, and append-only audit log.",
    version="0.1.0",
    lifespan=lifespan,
)

# POC: allow the browser UI (any origin) to call the API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(evals.router)
app.include_router(eval_agent_mapping.router)
app.include_router(calibration_sets.router)
app.include_router(change_events.router)
app.include_router(eval_results.router)
app.include_router(regression_alerts.router)
app.include_router(audit_log.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "governance-api"}

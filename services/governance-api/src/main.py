from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy import text

from .config import settings
from .database import Base, engine
from .otel import init_tracing


def _ensure_columns() -> None:
    """Idempotent in-place schema patches for the POC (avoids forcing a reseed).

    Adds columns introduced by code without a full Alembic upgrade flow.
    Postgres-only; SQLite tests start from fresh metadata via create_all.
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(
            text("ALTER TABLE evals ADD COLUMN IF NOT EXISTS blocking BOOLEAN NOT NULL DEFAULT FALSE")
        )
        conn.execute(
            text("ALTER TABLE evals ADD COLUMN IF NOT EXISTS scope VARCHAR NOT NULL DEFAULT 'turn'")
        )
        conn.execute(
            text("ALTER TABLE eval_results ADD COLUMN IF NOT EXISTS session_id VARCHAR")
        )
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
        _ensure_columns()
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

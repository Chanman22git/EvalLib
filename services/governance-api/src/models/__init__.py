"""SQLAlchemy ORM models for the Governance Store.

Portable types are used deliberately so the same models run on Postgres (prod)
and SQLite (tests): `Uuid` maps to native UUID on PG / CHAR(32) elsewhere, and
`JSON` maps to JSONB on PG / TEXT-encoded JSON elsewhere.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    framework: Mapped[str] = mapped_column(String, default="custom")
    owner_team: Mapped[str] = mapped_column(String, default="unassigned")
    owner_email: Mapped[str] = mapped_column(String, default="")
    criticality: Mapped[str] = mapped_column(String, default="low")
    data_classification: Mapped[str] = mapped_column(String, default="internal")
    business_unit: Mapped[str] = mapped_column(String, default="unassigned")
    is_third_party: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )


class Eval(Base):
    __tablename__ = "evals"
    __table_args__ = (UniqueConstraint("eval_id", "version", name="uq_eval_id_version"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    eval_id: Mapped[str] = mapped_column(String, index=True)
    version: Mapped[str] = mapped_column(String, default="1.0.0")
    criterion_description: Mapped[str] = mapped_column(Text, default="")
    evaluator_type: Mapped[str] = mapped_column(String, default="llm_as_judge")
    judge_config: Mapped[dict] = mapped_column(JSON, default=dict)
    prompt_template: Mapped[str | None] = mapped_column(Text, default=None)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict)
    retrieval_config: Mapped[dict | None] = mapped_column(JSON, default=None)
    calibration_set_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("calibration_sets.id"), default=None
    )
    last_judge_human_agreement: Mapped[float | None] = mapped_column(Float, default=None)
    agreement_threshold: Mapped[float] = mapped_column(Float, default=0.75)
    execution_modes: Mapped[dict] = mapped_column(JSON, default=dict)
    owner_team: Mapped[str] = mapped_column(String, default="unassigned")
    owner_email: Mapped[str] = mapped_column(String, default="")
    approver_email: Mapped[str | None] = mapped_column(String, default=None)
    review_status: Mapped[str] = mapped_column(String, default="draft", index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    # If True, this eval failing causes the agent's whole suite to FAIL
    # regardless of the mean score. Set at creation; immutable once approved.
    blocking: Mapped[bool] = mapped_column(Boolean, default=False)
    # Evaluation granularity: "turn" judges one trace/turn; "session" judges a
    # whole conversation transcript. Drives which suite path picks the eval up.
    scope: Mapped[str] = mapped_column(String, default="turn", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    calibration_set: Mapped["CalibrationSet | None"] = relationship(lazy="joined")


class EvalAgentMapping(Base):
    __tablename__ = "eval_agent_mapping"
    __table_args__ = (UniqueConstraint("eval_id", "agent_id", name="uq_eval_agent"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    eval_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("evals.id"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agents.id"), index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sample_rate: Mapped[float] = mapped_column(Float, default=1.0)


class CalibrationSet(Base):
    __tablename__ = "calibration_sets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    examples: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    event_type: Mapped[str] = mapped_column(String, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, default=None, index=True)
    actor: Mapped[str] = mapped_column(String, default="system")
    before: Mapped[dict] = mapped_column(JSON, default=dict)
    after: Mapped[dict] = mapped_column(JSON, default=dict)
    reason: Mapped[str | None] = mapped_column(Text, default=None)


class EvalResult(Base):
    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    trace_id: Mapped[str] = mapped_column(String, index=True)
    span_id: Mapped[str | None] = mapped_column(String, default=None)
    # Conversation grouping. Set on every result so per-turn and session-scoped
    # verdicts can be grouped into one thread in the UI. Null for legacy rows.
    session_id: Mapped[str | None] = mapped_column(String, default=None, index=True)
    eval_id: Mapped[str] = mapped_column(String, index=True)
    eval_version: Mapped[str] = mapped_column(String, default="1.0.0")
    verdict: Mapped[str] = mapped_column(String, default="")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[str | None] = mapped_column(Text, default=None)
    judge_model: Mapped[str | None] = mapped_column(String, default=None)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("agents.id"), default=None, index=True
    )


class RegressionAlert(Base):
    __tablename__ = "regression_alerts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("agents.id"), index=True)
    eval_id: Mapped[str] = mapped_column(String, index=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    baseline_score: Mapped[float] = mapped_column(Float, default=0.0)
    current_score: Mapped[float] = mapped_column(Float, default=0.0)
    delta: Mapped[float] = mapped_column(Float, default=0.0)
    candidate_causes: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="open", index=True)


class AuditLog(Base):
    """Append-only audit trail. The API never updates or deletes rows here."""

    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=_uuid)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, index=True)
    actor: Mapped[str] = mapped_column(String, default="system")
    action: Mapped[str] = mapped_column(String, index=True)
    entity_type: Mapped[str] = mapped_column(String, index=True)
    entity_id: Mapped[str] = mapped_column(String, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from ..enums import (
    AgentStatus,
    Criticality,
    DataClassification,
    EvaluatorType,
    RegressionStatus,
    ReviewStatus,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Agents ───────────────────────────────────────────────────────────────────
class AgentCreate(BaseModel):
    name: str
    description: str | None = None
    framework: str = "custom"
    owner_team: str = "unassigned"
    owner_email: str = ""
    criticality: Criticality = Criticality.low
    data_classification: DataClassification = DataClassification.internal
    business_unit: str = "unassigned"
    is_third_party: bool = False


class AgentUpdate(BaseModel):
    description: str | None = None
    framework: str | None = None
    owner_team: str | None = None
    owner_email: str | None = None
    criticality: Criticality | None = None
    data_classification: DataClassification | None = None
    business_unit: str | None = None
    is_third_party: bool | None = None
    status: AgentStatus | None = None


class AgentOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    framework: str
    owner_team: str
    owner_email: str
    criticality: str
    data_classification: str
    business_unit: str
    is_third_party: bool
    status: str
    created_at: datetime
    updated_at: datetime


# ── Calibration sets ──────────────────────────────────────────────────────────
class CalibrationExample(BaseModel):
    input: str
    output: str
    human_verdict: str
    rater_count: int = 1
    agreement: float = 1.0


class CalibrationSetCreate(BaseModel):
    name: str
    description: str | None = None
    examples: list[CalibrationExample] = Field(default_factory=list)


class CalibrationSetOut(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    examples: list[dict[str, Any]]
    created_at: datetime


# ── Evals ─────────────────────────────────────────────────────────────────────
class EvalCreate(BaseModel):
    eval_id: str
    version: str = "1.0.0"
    criterion_description: str = ""
    evaluator_type: EvaluatorType = EvaluatorType.llm_as_judge
    judge_config: dict[str, Any] = Field(default_factory=dict)
    prompt_template: str | None = None
    output_schema: dict[str, Any] = Field(default_factory=dict)
    retrieval_config: dict[str, Any] | None = None
    agreement_threshold: float = 0.75
    execution_modes: dict[str, Any] = Field(default_factory=dict)
    owner_team: str = "unassigned"
    owner_email: str = ""
    expires_at: datetime | None = None
    # If True, a failure of this eval makes the agent's whole suite FAIL.
    blocking: bool = False
    # Optional: auto-create eval→agent mappings at creation time.
    agent_ids: list[uuid.UUID] = Field(default_factory=list)


class EvalUpdate(BaseModel):
    criterion_description: str | None = None
    evaluator_type: EvaluatorType | None = None
    judge_config: dict[str, Any] | None = None
    prompt_template: str | None = None
    output_schema: dict[str, Any] | None = None
    retrieval_config: dict[str, Any] | None = None
    agreement_threshold: float | None = None
    execution_modes: dict[str, Any] | None = None
    owner_team: str | None = None
    owner_email: str | None = None
    expires_at: datetime | None = None


class EvalOut(ORMModel):
    id: uuid.UUID
    eval_id: str
    version: str
    criterion_description: str
    evaluator_type: str
    judge_config: dict[str, Any]
    prompt_template: str | None
    output_schema: dict[str, Any]
    retrieval_config: dict[str, Any] | None
    calibration_set_id: uuid.UUID | None
    last_judge_human_agreement: float | None
    agreement_threshold: float
    execution_modes: dict[str, Any]
    owner_team: str
    owner_email: str
    approver_email: str | None
    review_status: str
    approved_at: datetime | None
    expires_at: datetime | None
    blocking: bool
    created_at: datetime
    updated_at: datetime


class ApproveBody(BaseModel):
    approver_email: EmailStr
    actor: str = "ui"


class ActorBody(BaseModel):
    actor: str = "ui"


class AttachCalibrationBody(BaseModel):
    calibration_set_id: uuid.UUID
    actor: str = "ui"


# ── Eval-agent mapping ────────────────────────────────────────────────────────
class EvalAgentMappingCreate(BaseModel):
    eval_id: uuid.UUID
    agent_id: uuid.UUID
    enabled: bool = True
    sample_rate: float = 1.0


class EvalAgentMappingOut(ORMModel):
    id: uuid.UUID
    eval_id: uuid.UUID
    agent_id: uuid.UUID
    enabled: bool
    sample_rate: float


# ── Change events ─────────────────────────────────────────────────────────────
class ChangeEventCreate(BaseModel):
    event_type: str
    timestamp: datetime | None = None
    agent_id: uuid.UUID | None = None
    actor: str = "system"
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class ChangeEventOut(ORMModel):
    id: uuid.UUID
    event_type: str
    timestamp: datetime
    agent_id: uuid.UUID | None
    actor: str
    before: dict[str, Any]
    after: dict[str, Any]
    reason: str | None


# ── Eval results ──────────────────────────────────────────────────────────────
class EvalResultCreate(BaseModel):
    trace_id: str
    span_id: str | None = None
    eval_id: str
    eval_version: str = "1.0.0"
    verdict: str
    score: float
    reasoning: str | None = None
    judge_model: str | None = None
    evaluated_at: datetime | None = None
    agent_id: uuid.UUID | None = None


class EvalResultOut(ORMModel):
    id: uuid.UUID
    trace_id: str
    span_id: str | None
    eval_id: str
    eval_version: str
    verdict: str
    score: float
    reasoning: str | None
    judge_model: str | None
    evaluated_at: datetime
    agent_id: uuid.UUID | None


class EvalResultAggregate(BaseModel):
    agent_id: uuid.UUID | None
    eval_id: str
    count: int
    avg_score: float
    pass_rate: float


# ── Regression alerts ─────────────────────────────────────────────────────────
class RegressionAlertCreate(BaseModel):
    agent_id: uuid.UUID
    eval_id: str
    baseline_score: float
    current_score: float
    delta: float
    candidate_causes: list[dict[str, Any]] = Field(default_factory=list)


class RegressionAlertUpdate(BaseModel):
    status: RegressionStatus


class RegressionAlertOut(ORMModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    eval_id: str
    detected_at: datetime
    baseline_score: float
    current_score: float
    delta: float
    candidate_causes: list[dict[str, Any]]
    status: str


# ── Audit log ─────────────────────────────────────────────────────────────────
class AuditLogOut(ORMModel):
    id: uuid.UUID
    timestamp: datetime
    actor: str
    action: str
    entity_type: str
    entity_id: str
    detail: dict[str, Any]

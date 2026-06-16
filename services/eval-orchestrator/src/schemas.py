from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class TraceRef(BaseModel):
    """A trace (and optionally span) to evaluate.

    `input`/`output` may be supplied inline (the demo does this for determinism).
    When omitted, the orchestrator fetches them from Phoenix.
    """

    trace_id: str
    span_id: str | None = None
    session_id: str | None = None
    input: str | None = None
    output: str | None = None
    agent_id: uuid.UUID | None = None


class RunEvalRequest(BaseModel):
    eval_id: str
    version: str | None = None
    traces: list[TraceRef] = Field(default_factory=list)
    judge_model: str | None = None


class EvalVerdict(BaseModel):
    trace_id: str
    span_id: str | None
    session_id: str | None = None
    eval_id: str
    eval_version: str
    verdict: str
    score: float
    reasoning: str
    judge_model: str
    passed: bool
    error: str | None = None


class RunEvalResponse(BaseModel):
    eval_id: str
    eval_version: str
    count: int
    results: list[EvalVerdict]


class SampleRunResponse(BaseModel):
    sampled: int
    evaluated: int
    results: list[EvalVerdict] = Field(default_factory=list)


# ── Suite scoring (agent's full approved+mapped suite on one trace) ─────────
class ScoreRequest(BaseModel):
    agent: str  # agent uuid or name
    trace: TraceRef
    eval_ids: list[str] | None = None  # optional subset


class ConsolidatedScore(BaseModel):
    status: str  # "PASS" | "FAIL"
    mean_score: float
    threshold: float
    pass_count: int
    fail_count: int
    blocking_failures: list[str]
    reasons: list[str]


class ScoreResponse(BaseModel):
    agent_id: str | None
    agent_name: str | None
    trace_id: str
    results: list[EvalVerdict]
    consolidated: ConsolidatedScore


# ── Session scoring (session-scoped suite over a whole conversation) ─────────
class SessionRef(BaseModel):
    """A conversation: an ordered list of turns sharing one session_id."""

    session_id: str
    turns: list[TraceRef] = Field(default_factory=list)


class ScoreSessionRequest(BaseModel):
    agent: str  # agent uuid or name
    session: SessionRef
    eval_ids: list[str] | None = None  # optional subset


class ScoreSessionResponse(BaseModel):
    agent_id: str | None
    agent_name: str | None
    session_id: str
    turn_count: int
    results: list[EvalVerdict]
    consolidated: ConsolidatedScore


class JudgeOutput(BaseModel):
    verdict: str
    score: float
    reasoning: str = ""
    passed: bool | None = None


# Convenience alias for raw governance payloads.
JsonObj = dict[str, Any]

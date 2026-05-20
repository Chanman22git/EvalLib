from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Criticality(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class DataClassification(str, Enum):
    public = "public"
    internal = "internal"
    confidential = "confidential"
    restricted = "restricted"


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class AgentContext(BaseModel):
    """Enterprise governance context attached to every gateway call."""

    agent_id: str
    framework: str = "custom"
    criticality: Criticality = Criticality.low
    data_classification: DataClassification = DataClassification.internal
    business_unit: str = "unassigned"


class ChatRequest(BaseModel):
    model: str | None = None
    provider: str = "anthropic"
    messages: list[Message]
    temperature: float = 0.7
    max_tokens: int = 1024
    operation_name: str = "chat"  # gen_ai.operation.name (chat|execute_tool|invoke_agent)
    agent: AgentContext


class Usage(BaseModel):
    input_tokens: int
    output_tokens: int


class ChatResponse(BaseModel):
    id: str
    model: str
    provider: str
    content: str
    finish_reason: str
    usage: Usage
    trace_id: str
    span_id: str


class ChangeEventType(str, Enum):
    model_version_change = "model_version_change"
    prompt_change = "prompt_change"
    routing_change = "routing_change"
    tool_change = "tool_change"
    agent_lifecycle = "agent_lifecycle"


class ChangeEventRequest(BaseModel):
    event_type: ChangeEventType
    agent_id: str | None = None
    actor: str = "gateway"
    before: dict[str, Any] = Field(default_factory=dict)
    after: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None

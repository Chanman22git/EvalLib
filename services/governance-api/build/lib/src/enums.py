from __future__ import annotations

from enum import Enum


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


class AgentStatus(str, Enum):
    active = "active"
    deprecated = "deprecated"
    retired = "retired"


class EvaluatorType(str, Enum):
    llm_as_judge = "llm_as_judge"
    deterministic = "deterministic"
    embedding = "embedding"
    hybrid = "hybrid"


class ReviewStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    approved = "approved"
    deprecated = "deprecated"
    expired = "expired"


class RegressionStatus(str, Enum):
    open = "open"
    investigating = "investigating"
    resolved = "resolved"
    dismissed = "dismissed"

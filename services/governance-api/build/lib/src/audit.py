"""Append-only audit log writes (NFR-8).

Every governance state transition — agent registration/retirement, eval
creation, and each eval review-status change — is recorded here. The API exposes
no update or delete path for `audit_log`, so the trail is immutable in practice.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from .models import AuditLog


def record(
    db: Session,
    *,
    actor: str,
    action: str,
    entity_type: str,
    entity_id: str,
    detail: dict[str, Any] | None = None,
) -> AuditLog:
    entry = AuditLog(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        detail=detail or {},
    )
    db.add(entry)
    return entry

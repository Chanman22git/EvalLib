from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import ChangeEvent
from ..schemas import ChangeEventCreate, ChangeEventOut

router = APIRouter(prefix="/change-events", tags=["change-events"])


@router.post("", response_model=ChangeEventOut, status_code=201)
def ingest_change_event(body: ChangeEventCreate, db: Session = Depends(get_db)) -> ChangeEvent:
    event = ChangeEvent(
        event_type=body.event_type,
        agent_id=body.agent_id,
        actor=body.actor,
        before=body.before,
        after=body.after,
        reason=body.reason,
    )
    if body.timestamp is not None:
        event.timestamp = body.timestamp
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("", response_model=list[ChangeEventOut])
def query_change_events(
    db: Session = Depends(get_db),
    event_type: str | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None),
    actor: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=200, le=1000),
) -> list[ChangeEvent]:
    stmt = select(ChangeEvent)
    if event_type:
        stmt = stmt.where(ChangeEvent.event_type == event_type)
    if agent_id:
        stmt = stmt.where(ChangeEvent.agent_id == agent_id)
    if actor:
        stmt = stmt.where(ChangeEvent.actor == actor)
    if from_:
        stmt = stmt.where(ChangeEvent.timestamp >= from_)
    if to:
        stmt = stmt.where(ChangeEvent.timestamp <= to)
    return list(db.scalars(stmt.order_by(ChangeEvent.timestamp.desc()).limit(limit)))

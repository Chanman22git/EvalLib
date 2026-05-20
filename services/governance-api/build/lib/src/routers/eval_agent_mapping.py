from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Agent, Eval, EvalAgentMapping
from ..schemas import EvalAgentMappingCreate, EvalAgentMappingOut

router = APIRouter(prefix="/eval-agent-mapping", tags=["eval-agent-mapping"])


@router.post("", response_model=EvalAgentMappingOut, status_code=201)
def create_mapping(body: EvalAgentMappingCreate, db: Session = Depends(get_db)) -> EvalAgentMapping:
    if db.get(Eval, body.eval_id) is None:
        raise HTTPException(status_code=404, detail=f"Eval {body.eval_id} not found")
    if db.get(Agent, body.agent_id) is None:
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id} not found")
    mapping = EvalAgentMapping(
        eval_id=body.eval_id,
        agent_id=body.agent_id,
        enabled=body.enabled,
        sample_rate=body.sample_rate,
    )
    db.add(mapping)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Mapping already exists") from exc
    db.refresh(mapping)
    return mapping


@router.get("", response_model=list[EvalAgentMappingOut])
def list_mappings(
    db: Session = Depends(get_db),
    agent_id: uuid.UUID | None = Query(default=None),
    eval_id: uuid.UUID | None = Query(default=None),
) -> list[EvalAgentMapping]:
    stmt = select(EvalAgentMapping)
    if agent_id:
        stmt = stmt.where(EvalAgentMapping.agent_id == agent_id)
    if eval_id:
        stmt = stmt.where(EvalAgentMapping.eval_id == eval_id)
    return list(db.scalars(stmt))

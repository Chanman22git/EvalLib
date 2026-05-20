from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..enums import AgentStatus
from ..models import Agent
from ..schemas import AgentCreate, AgentOut, AgentUpdate
from . import get_or_404

router = APIRouter(prefix="/agents", tags=["agents"])


@router.post("", response_model=AgentOut, status_code=201)
def create_agent(body: AgentCreate, db: Session = Depends(get_db)) -> Agent:
    agent = Agent(
        name=body.name,
        description=body.description,
        framework=body.framework,
        owner_team=body.owner_team,
        owner_email=body.owner_email,
        criticality=body.criticality.value,
        data_classification=body.data_classification.value,
        business_unit=body.business_unit,
        is_third_party=body.is_third_party,
    )
    db.add(agent)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Agent name '{body.name}' already exists") from exc
    audit.record(
        db, actor=body.owner_email or "system", action="agent.register",
        entity_type="agent", entity_id=agent.id, detail={"name": agent.name},
    )
    db.commit()
    db.refresh(agent)
    return agent


@router.get("", response_model=list[AgentOut])
def list_agents(
    db: Session = Depends(get_db),
    criticality: str | None = Query(default=None),
    framework: str | None = Query(default=None),
    business_unit: str | None = Query(default=None),
    is_third_party: bool | None = Query(default=None),
    status: str | None = Query(default=None),
) -> list[Agent]:
    stmt = select(Agent)
    if criticality:
        stmt = stmt.where(Agent.criticality == criticality)
    if framework:
        stmt = stmt.where(Agent.framework == framework)
    if business_unit:
        stmt = stmt.where(Agent.business_unit == business_unit)
    if is_third_party is not None:
        stmt = stmt.where(Agent.is_third_party == is_third_party)
    if status:
        stmt = stmt.where(Agent.status == status)
    return list(db.scalars(stmt.order_by(Agent.created_at.desc())))


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> Agent:
    return get_or_404(db, Agent, agent_id, "Agent")


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(agent_id: uuid.UUID, body: AgentUpdate, db: Session = Depends(get_db)) -> Agent:
    agent = get_or_404(db, Agent, agent_id, "Agent")
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(agent, key, value.value if hasattr(value, "value") else value)
    audit.record(
        db, actor="ui", action="agent.update", entity_type="agent",
        entity_id=agent.id, detail={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}", response_model=AgentOut)
def retire_agent(agent_id: uuid.UUID, db: Session = Depends(get_db)) -> Agent:
    """Soft delete: set status=retired (FR-GS-2)."""
    agent = get_or_404(db, Agent, agent_id, "Agent")
    agent.status = AgentStatus.retired.value
    audit.record(
        db, actor="ui", action="agent.retire", entity_type="agent",
        entity_id=agent.id, detail={"name": agent.name},
    )
    db.commit()
    db.refresh(agent)
    return agent

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import audit, state_machine
from ..database import get_db
from ..models import Agent, CalibrationSet, Eval, EvalAgentMapping
from ..schemas import (
    ActorBody,
    ApproveBody,
    AttachCalibrationBody,
    EvalCreate,
    EvalOut,
    EvalUpdate,
)
from ..state_machine import TransitionError
from . import get_or_404

router = APIRouter(prefix="/evals", tags=["evals"])


def _bad_request_on_transition_error(exc: TransitionError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(exc))


@router.post("", response_model=EvalOut, status_code=201)
def create_eval(body: EvalCreate, db: Session = Depends(get_db)) -> Eval:
    ev = Eval(
        eval_id=body.eval_id,
        version=body.version,
        criterion_description=body.criterion_description,
        evaluator_type=body.evaluator_type.value,
        judge_config=body.judge_config,
        prompt_template=body.prompt_template,
        output_schema=body.output_schema,
        retrieval_config=body.retrieval_config,
        agreement_threshold=body.agreement_threshold,
        execution_modes=body.execution_modes,
        owner_team=body.owner_team,
        owner_email=body.owner_email,
        expires_at=body.expires_at,
        blocking=body.blocking,
        scope=body.scope,
    )
    db.add(ev)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Eval ({body.eval_id}, {body.version}) already exists",
        ) from exc

    # Auto-create eval→agent mappings if requested. Unknown agent_ids => 404.
    for agent_id in body.agent_ids:
        if db.get(Agent, agent_id) is None:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
        db.add(EvalAgentMapping(eval_id=ev.id, agent_id=agent_id, enabled=True, sample_rate=1.0))

    audit.record(
        db, actor=body.owner_email or "system", action="eval.create",
        entity_type="eval", entity_id=ev.id,
        detail={"eval_id": ev.eval_id, "version": ev.version, "blocking": ev.blocking,
                "scope": ev.scope, "attached_agents": [str(a) for a in body.agent_ids]},
    )
    db.commit()
    db.refresh(ev)
    return ev


@router.get("", response_model=list[EvalOut])
def list_evals(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    owner_team: str | None = Query(default=None),
    evaluator_type: str | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None),
) -> list[Eval]:
    stmt = select(Eval)
    if status:
        stmt = stmt.where(Eval.review_status == status)
    if owner_team:
        stmt = stmt.where(Eval.owner_team == owner_team)
    if evaluator_type:
        stmt = stmt.where(Eval.evaluator_type == evaluator_type)
    if agent_id:
        mapped = select(EvalAgentMapping.eval_id).where(EvalAgentMapping.agent_id == agent_id)
        stmt = stmt.where(Eval.id.in_(mapped))
    return list(db.scalars(stmt.order_by(Eval.created_at.desc())))


@router.get("/{eval_pk}", response_model=EvalOut)
def get_eval(eval_pk: uuid.UUID, db: Session = Depends(get_db)) -> Eval:
    return get_or_404(db, Eval, eval_pk, "Eval")


@router.patch("/{eval_pk}", response_model=EvalOut)
def update_eval(eval_pk: uuid.UUID, body: EvalUpdate, db: Session = Depends(get_db)) -> Eval:
    ev = get_or_404(db, Eval, eval_pk, "Eval")
    try:
        state_machine.ensure_editable(ev)
    except TransitionError as exc:
        raise _bad_request_on_transition_error(exc) from exc
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(ev, key, value.value if hasattr(value, "value") else value)
    audit.record(
        db, actor="ui", action="eval.update", entity_type="eval",
        entity_id=ev.id, detail={"fields": list(data.keys())},
    )
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/{eval_pk}/submit-for-review", response_model=EvalOut)
def submit_for_review(eval_pk: uuid.UUID, body: ActorBody, db: Session = Depends(get_db)) -> Eval:
    ev = get_or_404(db, Eval, eval_pk, "Eval")
    try:
        state_machine.submit_for_review(db, ev, body.actor)
    except TransitionError as exc:
        db.rollback()
        raise _bad_request_on_transition_error(exc) from exc
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/{eval_pk}/approve", response_model=EvalOut)
def approve(eval_pk: uuid.UUID, body: ApproveBody, db: Session = Depends(get_db)) -> Eval:
    ev = get_or_404(db, Eval, eval_pk, "Eval")
    try:
        state_machine.approve(db, ev, body.actor, str(body.approver_email))
    except TransitionError as exc:
        db.rollback()
        raise _bad_request_on_transition_error(exc) from exc
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/{eval_pk}/deprecate", response_model=EvalOut)
def deprecate(eval_pk: uuid.UUID, body: ActorBody, db: Session = Depends(get_db)) -> Eval:
    ev = get_or_404(db, Eval, eval_pk, "Eval")
    try:
        state_machine.deprecate(db, ev, body.actor)
    except TransitionError as exc:
        db.rollback()
        raise _bad_request_on_transition_error(exc) from exc
    db.commit()
    db.refresh(ev)
    return ev


@router.post("/{eval_pk}/calibration", response_model=EvalOut)
def attach_calibration(
    eval_pk: uuid.UUID, body: AttachCalibrationBody, db: Session = Depends(get_db)
) -> Eval:
    """Attach a calibration set and run the agreement test.

    The POC simulates a judge-vs-human agreement run by averaging the per-example
    agreement scores in the calibration set. The result is stored on the eval as
    `last_judge_human_agreement`, gating approval (FR-GS-3).
    """
    ev = get_or_404(db, Eval, eval_pk, "Eval")
    try:
        state_machine.ensure_editable(ev)
    except TransitionError as exc:
        raise _bad_request_on_transition_error(exc) from exc

    cal = get_or_404(db, CalibrationSet, body.calibration_set_id, "CalibrationSet")
    examples = cal.examples or []
    if not examples:
        raise HTTPException(status_code=400, detail="Calibration set has no examples")
    agreement = sum(float(e.get("agreement", 0.0)) for e in examples) / len(examples)

    ev.calibration_set_id = cal.id
    ev.last_judge_human_agreement = round(agreement, 4)
    audit.record(
        db, actor=body.actor, action="eval.calibration", entity_type="eval",
        entity_id=ev.id,
        detail={
            "calibration_set_id": str(cal.id),
            "agreement": ev.last_judge_human_agreement,
            "threshold": ev.agreement_threshold,
            "passed": ev.last_judge_human_agreement >= ev.agreement_threshold,
        },
    )
    db.commit()
    db.refresh(ev)
    return ev

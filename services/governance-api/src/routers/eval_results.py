from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import EvalResult
from ..schemas import EvalResultAggregate, EvalResultCreate, EvalResultOut

router = APIRouter(prefix="/eval-results", tags=["eval-results"])

# Verdicts considered a "pass" for pass-rate computations.
PASS_VERDICTS = {"compliant", "correct", "grounded", "pass", "passed", "helpful", "safe"}


@router.post("", response_model=EvalResultOut, status_code=201)
def create_eval_result(body: EvalResultCreate, db: Session = Depends(get_db)) -> EvalResult:
    result = EvalResult(
        trace_id=body.trace_id,
        span_id=body.span_id,
        eval_id=body.eval_id,
        eval_version=body.eval_version,
        verdict=body.verdict,
        score=body.score,
        reasoning=body.reasoning,
        judge_model=body.judge_model,
        agent_id=body.agent_id,
    )
    if body.evaluated_at is not None:
        result.evaluated_at = body.evaluated_at
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


@router.get("", response_model=list[EvalResultOut])
def query_eval_results(
    db: Session = Depends(get_db),
    trace_id: str | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None),
    eval_id: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    limit: int = Query(default=200, le=2000),
) -> list[EvalResult]:
    stmt = select(EvalResult)
    if trace_id:
        stmt = stmt.where(EvalResult.trace_id == trace_id)
    if agent_id:
        stmt = stmt.where(EvalResult.agent_id == agent_id)
    if eval_id:
        stmt = stmt.where(EvalResult.eval_id == eval_id)
    if from_:
        stmt = stmt.where(EvalResult.evaluated_at >= from_)
    if to:
        stmt = stmt.where(EvalResult.evaluated_at <= to)
    return list(db.scalars(stmt.order_by(EvalResult.evaluated_at.desc()).limit(limit)))


@router.get("/aggregate", response_model=list[EvalResultAggregate])
def aggregate_eval_results(
    db: Session = Depends(get_db),
    agent_id: uuid.UUID | None = Query(default=None),
    eval_id: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
) -> list[EvalResultAggregate]:
    """Aggregate scores per (agent, eval). pass_rate uses PASS_VERDICTS."""
    stmt = select(
        EvalResult.agent_id,
        EvalResult.eval_id,
        func.count().label("count"),
        func.avg(EvalResult.score).label("avg_score"),
    )
    if agent_id:
        stmt = stmt.where(EvalResult.agent_id == agent_id)
    if eval_id:
        stmt = stmt.where(EvalResult.eval_id == eval_id)
    if from_:
        stmt = stmt.where(EvalResult.evaluated_at >= from_)
    if to:
        stmt = stmt.where(EvalResult.evaluated_at <= to)
    stmt = stmt.group_by(EvalResult.agent_id, EvalResult.eval_id)

    out: list[EvalResultAggregate] = []
    for row in db.execute(stmt):
        # pass_rate computed with a second targeted query for portability.
        pass_stmt = select(func.count()).where(EvalResult.eval_id == row.eval_id)
        total_stmt = select(func.count()).where(EvalResult.eval_id == row.eval_id)
        if row.agent_id is not None:
            pass_stmt = pass_stmt.where(EvalResult.agent_id == row.agent_id)
            total_stmt = total_stmt.where(EvalResult.agent_id == row.agent_id)
        pass_stmt = pass_stmt.where(EvalResult.verdict.in_(PASS_VERDICTS))
        if from_:
            pass_stmt = pass_stmt.where(EvalResult.evaluated_at >= from_)
            total_stmt = total_stmt.where(EvalResult.evaluated_at >= from_)
        if to:
            pass_stmt = pass_stmt.where(EvalResult.evaluated_at <= to)
            total_stmt = total_stmt.where(EvalResult.evaluated_at <= to)
        passes = db.scalar(pass_stmt) or 0
        total = db.scalar(total_stmt) or 1
        out.append(
            EvalResultAggregate(
                agent_id=row.agent_id,
                eval_id=row.eval_id,
                count=row.count,
                avg_score=round(float(row.avg_score or 0.0), 4),
                pass_rate=round(passes / total, 4),
            )
        )
    return out

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import audit
from ..database import get_db
from ..models import RegressionAlert
from ..schemas import RegressionAlertCreate, RegressionAlertOut, RegressionAlertUpdate
from . import get_or_404

router = APIRouter(prefix="/regression-alerts", tags=["regression-alerts"])


@router.post("", response_model=RegressionAlertOut, status_code=201)
def create_alert(body: RegressionAlertCreate, db: Session = Depends(get_db)) -> RegressionAlert:
    alert = RegressionAlert(
        agent_id=body.agent_id,
        eval_id=body.eval_id,
        baseline_score=body.baseline_score,
        current_score=body.current_score,
        delta=body.delta,
        candidate_causes=body.candidate_causes,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.get("", response_model=list[RegressionAlertOut])
def list_alerts(
    db: Session = Depends(get_db),
    status: str | None = Query(default=None),
    agent_id: uuid.UUID | None = Query(default=None),
) -> list[RegressionAlert]:
    stmt = select(RegressionAlert)
    if status:
        stmt = stmt.where(RegressionAlert.status == status)
    if agent_id:
        stmt = stmt.where(RegressionAlert.agent_id == agent_id)
    return list(db.scalars(stmt.order_by(RegressionAlert.detected_at.desc())))


@router.get("/{alert_id}", response_model=RegressionAlertOut)
def get_alert(alert_id: uuid.UUID, db: Session = Depends(get_db)) -> RegressionAlert:
    return get_or_404(db, RegressionAlert, alert_id, "RegressionAlert")


@router.patch("/{alert_id}", response_model=RegressionAlertOut)
def update_alert(
    alert_id: uuid.UUID, body: RegressionAlertUpdate, db: Session = Depends(get_db)
) -> RegressionAlert:
    alert = get_or_404(db, RegressionAlert, alert_id, "RegressionAlert")
    alert.status = body.status.value
    audit.record(
        db, actor="ui", action="regression.status_change", entity_type="regression_alert",
        entity_id=alert.id, detail={"status": alert.status},
    )
    db.commit()
    db.refresh(alert)
    return alert

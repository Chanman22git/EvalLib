from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import CalibrationSet
from ..schemas import CalibrationSetCreate, CalibrationSetOut
from . import get_or_404

router = APIRouter(prefix="/calibration-sets", tags=["calibration-sets"])


@router.post("", response_model=CalibrationSetOut, status_code=201)
def create_calibration_set(body: CalibrationSetCreate, db: Session = Depends(get_db)) -> CalibrationSet:
    cal = CalibrationSet(
        name=body.name,
        description=body.description,
        examples=[e.model_dump() for e in body.examples],
    )
    db.add(cal)
    db.commit()
    db.refresh(cal)
    return cal


@router.get("", response_model=list[CalibrationSetOut])
def list_calibration_sets(db: Session = Depends(get_db)) -> list[CalibrationSet]:
    return list(db.scalars(select(CalibrationSet).order_by(CalibrationSet.created_at.desc())))


@router.get("/{cal_id}", response_model=CalibrationSetOut)
def get_calibration_set(cal_id: uuid.UUID, db: Session = Depends(get_db)) -> CalibrationSet:
    return get_or_404(db, CalibrationSet, cal_id, "CalibrationSet")

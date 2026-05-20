from __future__ import annotations

import uuid
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..database import Base

T = TypeVar("T", bound=Base)


def get_or_404(db: Session, model: type[T], entity_id: uuid.UUID, name: str = "Resource") -> T:
    obj = db.get(model, entity_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{name} {entity_id} not found")
    return obj

"""Eval governance state machine (FR-GS-3).

    draft ──submit──▶ in_review ──approve──▶ approved ──deprecate──▶ deprecated

Rules:
- An approved eval is immutable. Edits require creating a new version.
- Approval requires: a calibration set attached, human/judge agreement at or
  above the eval's threshold, and an approver_email.
- Every transition is written to the audit log and the change_events stream.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from . import audit
from .enums import ReviewStatus
from .models import ChangeEvent, Eval

# Allowed forward transitions.
_TRANSITIONS: dict[ReviewStatus, set[ReviewStatus]] = {
    ReviewStatus.draft: {ReviewStatus.in_review},
    ReviewStatus.in_review: {ReviewStatus.approved, ReviewStatus.draft},
    ReviewStatus.approved: {ReviewStatus.deprecated},
    ReviewStatus.deprecated: set(),
    ReviewStatus.expired: set(),
}

# Statuses in which an eval definition may still be edited.
EDITABLE_STATUSES = {ReviewStatus.draft, ReviewStatus.in_review}


class TransitionError(ValueError):
    """Raised when a requested governance transition is not permitted."""


def _log_transition(
    db: Session, ev: Eval, *, frm: ReviewStatus, to: ReviewStatus, actor: str
) -> None:
    audit.record(
        db,
        actor=actor,
        action=f"eval.{to.value}",
        entity_type="eval",
        entity_id=ev.id,
        detail={"eval_id": ev.eval_id, "version": ev.version, "from": frm.value, "to": to.value},
    )
    db.add(
        ChangeEvent(
            event_type="eval_lifecycle",
            actor=actor,
            before={"review_status": frm.value},
            after={"review_status": to.value, "eval_id": ev.eval_id, "version": ev.version},
            reason=f"Eval {ev.eval_id} {frm.value} → {to.value}",
        )
    )


def _assert_allowed(frm: ReviewStatus, to: ReviewStatus) -> None:
    if to not in _TRANSITIONS.get(frm, set()):
        raise TransitionError(f"Illegal transition: {frm.value} → {to.value}")


def submit_for_review(db: Session, ev: Eval, actor: str) -> Eval:
    frm = ReviewStatus(ev.review_status)
    _assert_allowed(frm, ReviewStatus.in_review)
    ev.review_status = ReviewStatus.in_review.value
    _log_transition(db, ev, frm=frm, to=ReviewStatus.in_review, actor=actor)
    return ev


def approve(db: Session, ev: Eval, actor: str, approver_email: str) -> Eval:
    frm = ReviewStatus(ev.review_status)
    _assert_allowed(frm, ReviewStatus.approved)

    # Approval guards.
    if ev.calibration_set_id is None:
        raise TransitionError("Cannot approve: no calibration set attached.")
    if not approver_email:
        raise TransitionError("Cannot approve: approver_email is required.")
    agreement = ev.last_judge_human_agreement
    if agreement is None or agreement < ev.agreement_threshold:
        raise TransitionError(
            f"Cannot approve: judge/human agreement {agreement} is below threshold "
            f"{ev.agreement_threshold}."
        )

    ev.review_status = ReviewStatus.approved.value
    ev.approver_email = approver_email
    ev.approved_at = datetime.now(timezone.utc)
    _log_transition(db, ev, frm=frm, to=ReviewStatus.approved, actor=actor)
    return ev


def deprecate(db: Session, ev: Eval, actor: str) -> Eval:
    frm = ReviewStatus(ev.review_status)
    _assert_allowed(frm, ReviewStatus.deprecated)
    ev.review_status = ReviewStatus.deprecated.value
    _log_transition(db, ev, frm=frm, to=ReviewStatus.deprecated, actor=actor)
    return ev


def ensure_editable(ev: Eval) -> None:
    if ReviewStatus(ev.review_status) not in EDITABLE_STATUSES:
        raise TransitionError(
            f"Eval is {ev.review_status} and is immutable. Create a new version to edit."
        )

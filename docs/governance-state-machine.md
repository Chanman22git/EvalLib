# Eval Governance State Machine

Every eval is versioned, owned, and **governance-gated** before it can run on
production traces. The state machine and its guards are the core of EvalLib's
governance value.

> Implemented in `services/governance-api/src/state_machine.py`; enforced by the
> `/evals/*` endpoints; surfaced in the UI by `EvalGovernanceActions`.

## States and transitions

```
   ┌─────────┐  submit-for-review   ┌───────────┐   approve    ┌──────────┐  deprecate  ┌────────────┐
   │  draft  │ ───────────────────▶ │ in_review │ ───────────▶ │ approved │ ──────────▶ │ deprecated │
   └─────────┘ ◀─────────────────── └───────────┘              └──────────┘             └────────────┘
        ▲          (back to draft)
        │
   (create eval)
```

- `expired` is a terminal state reserved for evals past `expires_at` (treated as
  not-runnable by the orchestrator).
- Transitions other than those drawn above return **400** with a clear message
  (`"Illegal transition: <from> → <to>"`).

## Guards

| Transition | Guard |
|---|---|
| `draft → in_review` | none |
| `in_review → approved` | **(1)** a calibration set is attached, **(2)** `last_judge_human_agreement ≥ agreement_threshold`, **(3)** `approver_email` supplied |
| `approved → deprecated` | none |
| editing an eval | only allowed in `draft` / `in_review`; an **approved eval is immutable** — create a new version to change it |

Failing any approval guard returns **400** and the state does **not** advance
(AC-9).

## Calibration / agreement

`POST /evals/{id}/calibration` attaches a calibration set and runs the agreement
test. For the POC, agreement is computed as the mean of the calibration set's
per-example `agreement` values and stored on the eval as
`last_judge_human_agreement`. Approval is gated on this meeting the eval's
`agreement_threshold` (default 0.75).

This is what drives the AC-5 demo flow: create → submit → approve **fails** on a
weak calibration set (agreement below threshold) → attach a stronger set →
approve **succeeds**.

## Audit trail (NFR-8)

Every transition writes:
1. an **append-only `audit_log`** row (`actor`, `action`, `entity_type`,
   `entity_id`, `detail`, `timestamp`) — the API exposes no update/delete path, and
2. a `change_events` row of type `eval_lifecycle`, so governance changes appear in
   the same change-event stream the regression detector mines.

Read the trail via `GET /audit-log?entity_type=eval&entity_id=<id>`; the UI shows
it on each eval's detail page.

## Why this matters

In a regulated environment, you must be able to show *which* eval ran, *what
version*, *who approved it*, *against what calibrated ground truth*, and *when* —
all as immutable evidence. The state machine + audit log produce exactly those
evidence-ready artifacts.

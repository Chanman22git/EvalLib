# Governance API

The enterprise-specific store and control plane that Phoenix does not provide:
the **agent registry**, the **eval registry with an approval state machine**, the
**change-event stream**, an **eval-results mirror** for fast querying, regression
alerts, and an **append-only audit log**.

Runs on **:8001**. OpenAPI docs at `/docs`.

## Data model (Postgres)

| Table | Purpose |
|---|---|
| `agents` | Agent registry (criticality, data classification, owner, BU, status) |
| `evals` | Eval definitions (versioned, owned, governance-gated) |
| `eval_agent_mapping` | Which evals run on which agents + sample rate |
| `calibration_sets` | Human-labeled ground truth for judges |
| `change_events` | Model/prompt/routing/tool/agent change stream |
| `eval_results` | Mirror of OTel eval events for fast time-series queries |
| `regression_alerts` | Detected regressions + ranked candidate causes |
| `audit_log` | Append-only trail of every governance transition (NFR-8) |

## Governance state machine (FR-GS-3)

```
draft ──submit-for-review──▶ in_review ──approve──▶ approved ──deprecate──▶ deprecated
```

- An **approved** eval is immutable — edits require a new version.
- **Approval guards:** a calibration set is attached, judge/human agreement ≥ the
  eval's threshold, and an `approver_email` is supplied. Failing any guard returns
  `400` with a clear message (AC-9).
- Every transition writes to `audit_log` **and** the `change_events` stream.

See [`src/state_machine.py`](src/state_machine.py).

## Key endpoints

`/agents`, `/evals` (+ `/submit-for-review`, `/approve`, `/deprecate`,
`/calibration`), `/eval-agent-mapping`, `/calibration-sets`, `/change-events`,
`/eval-results` (+ `/aggregate`), `/regression-alerts`, `/audit-log`.

## Migrations

The schema lives in the SQLAlchemy models and is materialised on startup
(`create_all`) for POC convenience. Alembic is wired for explicit migrations:

```bash
docker compose run --rm governance-api alembic upgrade head
```

## Tests

```bash
docker compose run --rm governance-api pytest -q
```

Tests run against in-memory SQLite (portable model types make this possible) and
cover a happy + error path per endpoint plus the full state machine, including
the AC-5 approval flow and the AC-9 below-threshold rejection.

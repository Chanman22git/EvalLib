# Architecture

EvalLib is a governance, evaluation, and experience layer that sits **above** the
existing observability stack (Phoenix / Datadog / Splunk), anchored on the
enterprise model gateway. It does not replace those backends — it emits
OpenTelemetry and adds the enterprise governance views and controls they lack.

## Components

```
        Enterprise Agents (LangGraph, CrewAI, custom, vendor)
                              │  all LLM calls
                              ▼
                   ┌──────────────────────┐
                   │   Mock Model Gateway  │  emits OTel GenAI spans
                   │      (:8080)          │  + change events
                   └───────────┬───────────┘
                  OTel spans    │   change events ──────────────┐
                                ▼                                │
                   ┌──────────────────────┐                     │
                   │   OTel Collector      │  PII redaction,     │
                   │   (:4317 / :4318)     │  enrichment, fan-out│
                   └───┬───────────┬───────┘                     │
            traces     │           │  traces                     │
                       ▼           ▼                             │
                ┌──────────┐  ┌───────────────────────┐          │
                │ Phoenix  │  │  Eval Orchestrator     │          │
                │ (:6006)  │◄─┤  (:8002)               │          │
                │ traces + │  │  offline + sampled      │          │
                │ evals    │  │  evals, regression job  │          │
                └────┬─────┘  └───────────┬────────────┘          │
                     │                    │ eval results,         │
                     │   ┌────────────────┘ regression alerts     │
                     ▼   ▼                                        ▼
              ┌───────────────────────┐     ┌──────────────────────┐
              │  Governance API        │────▶│  Postgres            │
              │  (:8001)               │     │  Governance Store    │
              │  registries, state     │◄────│  + append-only audit │
              │  machine, audit log    │     └──────────────────────┘
              └───────────┬────────────┘
                          │ REST + generated TS types
                          ▼
              ┌───────────────────────┐
              │  Experience UI (:3000) │  React + TS + Tailwind + shadcn
              └───────────────────────┘
```

| Component | Tech | Responsibility |
|---|---|---|
| **Mock Gateway** | FastAPI | Single LLM chokepoint; emits GenAI spans + change events. Mock provider by default, Anthropic behind `LLM_MODE`. |
| **OTel Collector** | otelcol-contrib | OTLP ingest, regex PII redaction (span + span-event attrs), resource enrichment, fan-out to Phoenix + file (+ optional Datadog/Splunk). |
| **Phoenix** | self-hosted Docker | Trace backend + eval execution engine. The POC does **not** duplicate Phoenix's trace UI. |
| **Governance API** | FastAPI + Postgres + SQLAlchemy/Alembic | Agent + eval registries, eval governance state machine, calibration sets, change events, eval-results mirror, regression alerts, append-only audit log. |
| **Eval Orchestrator** | FastAPI + `arize-phoenix-evals` | Runs evals on traces (offline + sampled-online), emits `gen_ai.evaluation.result`, runs the regression-detection job. |
| **Experience UI** | React 18 + Vite + TS + Tailwind + shadcn | Governance views for engineering, risk/compliance, and leadership. |

## Key architectural decisions

- **Phoenix is the trace backend and eval engine.** Traces are not stored in a
  separate database; the Governance Store holds only enterprise-specific data.
- **The Governance Store (Postgres) is the system of record** for the agent
  registry, eval registry (with approval workflow), change events, regression
  alerts, and an append-only audit log.
- **All LLM calls funnel through the gateway** — including eval judges — so the
  gateway stays the single observable chokepoint.
- **Eval results are dual-written**: a portable OTel `gen_ai.evaluation.result`
  event (for downstream backends, AC-8) **and** a Postgres mirror (for fast UI
  time-series queries).
- **The orchestrator polls Phoenix** for trace I/O rather than running a second
  OTLP receiver, avoiding duplicate span handling. Phoenix calls are best-effort;
  the OTel event + Postgres mirror are authoritative.
- **The UI consumes TypeScript types generated from the OpenAPI specs**, keeping
  frontend and backend in lock-step (`npm run gen:types`).

## Data flow: a live eval

1. An agent calls `POST /v1/chat` on the gateway with its governance context.
2. The gateway calls the provider and emits a GenAI span (→ collector → Phoenix +
   file). The response carries `trace_id` / `span_id`.
3. The orchestrator (offline `POST /run-eval`, or the sampled-online worker)
   resolves the approved eval, renders the judge prompt, and calls the judge
   **through the gateway**.
4. It validates the verdict, writes to the `eval_results` mirror, emits
   `gen_ai.evaluation.result` (linked to the origin span), and annotates Phoenix.
5. The regression job periodically compares score windows and, on a drop, writes
   a regression alert with ranked candidate causes and emits
   `enterprise.regression.detected`.
6. The UI reads the Governance API (and deep-links to Phoenix for span detail).

## Service ports

| Service | Port |
|---|---|
| Experience UI | 3000 |
| OTLP gRPC / HTTP (collector) | 4317 / 4318 |
| Phoenix | 6006 |
| Mock Gateway | 8080 |
| Governance API | 8001 |
| Eval Orchestrator | 8002 |
| Postgres | 5432 |

## Out of scope (this POC)

Inline gateway enforcement, self-healing remediation, multi-tenant isolation,
formal SR 11-7 / EU AI Act certification, real KB-backed retrieval, judge panels,
and production-scale multi-node deployment. See PRD §10.

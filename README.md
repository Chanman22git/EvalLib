# EvalLib

**An enterprise governance, evaluation, and experience layer for AI agents.**

EvalLib is *not* a re-implementation of Phoenix, Datadog, or Splunk. It is the
governance and control layer that sits **above** them, anchored on the enterprise
model gateway. A live LLM call flows through the gateway → a trace is captured →
an eval runs → the result is emitted as an OpenTelemetry event → it shows up in a
custom experience UI with full governance context (which eval ran, what version,
who approved it, the verdict, and a link to the trace).

> Status: POC. Local-first, single-node, `docker compose up`. See
> `PRD_agent_observability_poc.md` for the full specification.

## Architecture

```
        Enterprise Agents (LangGraph, CrewAI, custom, vendor)
                              │  all LLM calls
                              ▼
                   ┌──────────────────────┐
                   │   Mock Model Gateway  │  emits OTel GenAI spans
                   │      (:8080)          │  + change events
                   └───────────┬───────────┘
                  OTel spans    │   change events
                                ▼
                   ┌──────────────────────┐
                   │   OTel Collector      │  PII redaction, enrichment,
                   │   (:4317 / :4318)     │  fan-out
                   └───┬───────────┬───────┘
            traces     │           │   traces
                       ▼           ▼
                ┌──────────┐  ┌───────────────────────┐
                │ Phoenix  │  │  Eval Orchestrator     │
                │ (:6006)  │  │  (:8002)               │
                │ traces + │  │  samples traces,       │
                │ evals    │◄─┤  runs evals, emits     │
                └────┬─────┘  │  gen_ai.evaluation.result│
                     │        └───────────┬────────────┘
                     │                    │
                     │   ┌────────────────┘
                     ▼   ▼
              ┌───────────────────────┐     ┌──────────────────────┐
              │  Governance API        │────▶│  Postgres            │
              │  (:8001)               │     │  Governance Store    │
              │  agents, evals, state  │     │  + append-only audit │
              │  machine, audit log    │     └──────────────────────┘
              └───────────┬────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │  Experience UI (:3000) │  (Phase E)
              └───────────────────────┘
```

## Quickstart

Requirements: Docker + Docker Compose v2. (An Anthropic API key is optional —
the stack runs fully in mock mode by default.)

```bash
make setup     # creates .env from .env.example
make run       # build + start the stack
make seed      # populate demo data (after Phase D)
make demo      # end-to-end demo (after Phase D)
```

URLs once up:

| Service | URL |
|---|---|
| Experience UI | http://localhost:3000 *(Phase E)* |
| Phoenix | http://localhost:6006 |
| Governance API docs | http://localhost:8001/docs |
| Eval Orchestrator docs | http://localhost:8002/docs |
| Mock Gateway docs | http://localhost:8080/docs |

### Real LLM calls

Set in `.env`:

```
LLM_MODE=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Then `make up`. With `LLM_MODE=mock` (default) no network calls are made.

## Verify the foundation (Phase A)

With the stack up, send a call through the gateway and watch the trace appear in
Phoenix:

```bash
curl -s localhost:8080/v1/chat -H 'content-type: application/json' -d '{
  "messages": [{"role":"user","content":"What is your refund policy?"}],
  "agent": {"agent_id":"agent-support-refund","framework":"langgraph",
            "criticality":"critical","data_classification":"restricted",
            "business_unit":"retail-banking"}
}' | jq .
```

Open http://localhost:6006 → the trace shows up within a couple of seconds.
Raw telemetry (including redacted PII) is also written to
`otel-collector/output/otel-audit.jsonl`.

## Services

| Directory | What it is |
|---|---|
| [`services/mock-gateway`](services/mock-gateway) | Enterprise gateway stand-in; emits OTel GenAI spans |
| [`services/governance-api`](services/governance-api) | Agent + eval registry, governance state machine, audit log |
| [`services/eval-orchestrator`](services/eval-orchestrator) | Runs evals on traces via `arize-phoenix-evals`, emits OTel eval events |
| [`services/seed`](services/seed) | Demo data + sample eval definitions |
| [`services/ui`](services/ui) | Experience UI *(Phase E)* |
| [`otel-collector`](otel-collector) | OTLP ingestion, PII redaction, fan-out |

## Make targets

Run `make help` for the full list. Common ones: `setup`, `up`, `down`, `reset`,
`logs`, `ps`, `seed`, `demo`, `test`.

## Secrets

All secrets live in `.env` (git-ignored). Never commit real keys. See
[`.env.example`](.env.example).

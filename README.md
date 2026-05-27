# EvalLib

**An enterprise governance, evaluation, and experience layer for AI agents.**

> **Try it live:** the UI is hosted at <https://chanman22git.github.io/EvalLib/>.
> It's a static shell — the FastAPI services run on your machine. Clone this
> repo, `docker compose up`, then refresh the hosted page. Your browser will
> reach the backends at `http://localhost:8001` (`8002`, `6006`); modern
> browsers exempt localhost from mixed-content blocking, and the services ship
> with permissive CORS, so no extra setup is needed. For the chat agent, use
> `make chat` in your terminal.

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
              │  Experience UI (:3000) │
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
| Experience UI | http://localhost:3000 |
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
| [`services/ui`](services/ui) | Experience UI (React + TS + Tailwind + shadcn) |
| [`otel-collector`](otel-collector) | OTLP ingestion, PII redaction, fan-out |

## Talk to a grounded policy agent

A retrieval-grounded agent makes the loop concrete: it answers customer questions
using a real policy document (`kb/refund_policy.md`), routes every turn through the
gateway (so it's traced), and auto-runs its mapped eval.

```bash
make up && make seed          # stack + demo data
make chat                     # interactive REPL
# or one-shot:
python3 scripts/policy_agent.py -q "Can I get a refund 25 days after purchase?"
```

Each turn prints the grounded answer, the trace id, the eval verdict, and links to
Phoenix + the EvalLib trace page. The agent and the eval judge retrieve from the
**same** `kb/` document, so the judge grades against the exact policy text the
agent was given. In mock mode the answer quotes the retrieved policy and the
verdict is deterministic-but-arbitrary; set `LLM_MODE=anthropic` for real answers
and meaningful verdicts.

## Documentation

| Doc | What's in it |
|---|---|
| [`docs/architecture.md`](docs/architecture.md) | Components, key decisions, data flow, ports |
| [`docs/otel-conventions.md`](docs/otel-conventions.md) | Every OTel attribute we emit and why (GenAI semconv v1.37+) |
| [`docs/governance-state-machine.md`](docs/governance-state-machine.md) | Eval lifecycle, approval guards, audit trail |
| [`docs/demo-script.md`](docs/demo-script.md) | 5-minute walkthrough for all three audiences |
| [`docs/acceptance-criteria.md`](docs/acceptance-criteria.md) | AC-1…AC-12 status with evidence |

Each service also has its own `README.md` (see the table above).

## Make targets

Run `make help` for the full list. Common ones: `setup`, `up`, `down`, `reset`,
`logs`, `ps`, `seed`, `demo`, `test`.

## Secrets

All secrets live in `.env` (git-ignored). Never commit real keys. See
[`.env.example`](.env.example).

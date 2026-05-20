# Eval Orchestrator

Runs evals against traces and turns the verdicts into portable telemetry. Runs on
**:8002**. OpenAPI docs at `/docs`.

## What it does (FR-EO-1..5)

For each (eval, trace) pair:

1. Resolve trace input/output (inline, or fetched from Phoenix).
2. Verify the eval is **approved** and not expired (queried from the Governance API).
3. Retrieve context if the eval has `retrieval_config` (POC: mock KB in
   [`retrieval.py`](src/retrieval.py)).
4. Render the judge prompt using **`arize-phoenix-evals` `PromptTemplate`**.
5. Call the judge LLM **through the model gateway** (so all LLM traffic stays on
   the single observable chokepoint).
6. Parse + validate the output against the eval's `output_schema`; on a parse
   failure, retry once with a stricter instruction.
7. Persist to the Governance `eval_results` mirror, **emit a
   `gen_ai.evaluation.result` OTel event** linked to the original trace/span, and
   annotate the span in Phoenix (best-effort).

## Execution modes

| Mode | Trigger | Status |
|---|---|---|
| **Offline** | `POST /run-eval` `{eval_id, traces[]}` — synchronous | ✅ implemented |
| **Sampled-online** | background loop + `POST /sample-once` | ✅ implemented |
| **Inline** (gating) | `POST /inline-eval` | `501` — Phase 2 scaffold |

## OTel evaluation event (FR-EO-3)

Emitted as a span `evaluation <eval_id>` carrying a Link to the origin span and a
`gen_ai.evaluation.result` event with: `gen_ai.evaluation.name|version|verdict|
score|judge.model|judge.provider|reasoning|passed`. Inspect via the collector's
file exporter (AC-8):

```bash
grep gen_ai.evaluation.result otel-collector/output/otel-audit.jsonl | tail -1 | jq .
```

## Design notes

- **Phoenix calls are best-effort.** The authoritative outputs are the OTel event
  and the Governance Store mirror; a Phoenix API mismatch never fails an eval.
- **OTel pins track the Phoenix ecosystem** (1.42.x) because `arize-phoenix-evals`
  depends on them — newer than the gateway/governance services. Each service has
  its own image, so the skew is isolated.

## Tests

```bash
docker compose run --rm eval-orchestrator pytest -q
```

Covers regression-detection math, prompt rendering with retrieved context, judge
output parsing (happy/error/retry-inference), and the `/run-eval` endpoint
(happy / 404 / non-approved-400) plus the inline `501`.

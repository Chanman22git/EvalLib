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

## Regression detection (FR-RD-1..3)

A background job (every 15 min, or `POST /detect-regressions` on demand) compares,
per approved (agent, eval) pair, the **current** rolling window's mean score
against an older **baseline** window. A regression triggers when the current mean
is >2σ below baseline **or** drops >10 percentage points (`is_regression`).

On trigger it:
1. runs a **candidate-cause analysis** — the agent's change events in the last
   48h, ranked by temporal proximity to the regression onset (`rank_candidate_causes`),
2. persists a `regression_alert` (deduped against existing open alerts), and
3. emits an `enterprise.regression.detected` OTel event.

Windows are POC-tuned for the seed cadence (current = last 24h, baseline = days
2–7 ago) and configurable via `REGRESSION_*` env vars. The detection math and
cause ranking live in `regression_detector.py` for isolated unit testing.

```bash
grep enterprise.regression.detected otel-collector/output/otel-audit.jsonl | tail -1 | jq .
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

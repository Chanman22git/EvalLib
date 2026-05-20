# OpenTelemetry Conventions

EvalLib emits telemetry using the **OpenTelemetry GenAI Semantic Conventions
(target v1.37+)**, plus a small set of `enterprise.*` extension attributes for
governance context. Pinning the spec version is a deliberate risk mitigation
(PRD §11): GenAI conventions are still evolving, so we record exactly what we use
here and revisit on each minor spec release.

> Defined in `services/mock-gateway/src/otel_instrumentation.py` (request spans)
> and `services/eval-orchestrator/src/otel_emitter.py` (eval + regression events).

## 1. GenAI request spans (mock gateway)

Emitted once per LLM call as a `CLIENT` span named `<operation> <model>`.

| Attribute | Example | Notes |
|---|---|---|
| `gen_ai.operation.name` | `chat` | also `execute_tool`, `invoke_agent` |
| `gen_ai.provider.name` | `anthropic` | provider behind the gateway |
| `gen_ai.request.model` | `claude-sonnet-4-6` | |
| `gen_ai.request.temperature` | `0.2` | |
| `gen_ai.request.max_tokens` | `1024` | |
| `gen_ai.response.model` | `claude-sonnet-4-6` | as returned |
| `gen_ai.response.finish_reasons` | `["stop"]` | array |
| `gen_ai.usage.input_tokens` | `16` | |
| `gen_ai.usage.output_tokens` | `46` | |

### Enterprise extensions

| Attribute | Values |
|---|---|
| `enterprise.agent.id` | agent identifier |
| `enterprise.agent.framework` | `langgraph` / `crewai` / `custom` / `vendor` |
| `enterprise.agent.criticality` | `low` / `medium` / `high` / `critical` |
| `enterprise.agent.data_classification` | `public` / `internal` / `confidential` / `restricted` |
| `enterprise.business_unit` | business unit string |

### Message content capture

Controlled by `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT`. When `true`,
prompt/response content is attached as **span events** (`gen_ai.system.message`,
`gen_ai.user.message`, `gen_ai.assistant.message`, `gen_ai.choice`) with a
`content` attribute — per the OTel spec. This content is the primary PII vector,
so the collector redacts **span-event attributes** as well as span attributes
(see §4).

## 2. Eval result events (orchestrator) — `gen_ai.evaluation.result`

Each eval result is a span `evaluation <eval_id>` carrying a **Link** back to the
original `(trace_id, span_id)`, with a `gen_ai.evaluation.result` event:

| Attribute | Example |
|---|---|
| `gen_ai.evaluation.name` | `refund_policy_compliance` |
| `gen_ai.evaluation.version` | `1.0.0` |
| `gen_ai.evaluation.verdict` | `non_compliant` |
| `gen_ai.evaluation.score` | `0.15` |
| `gen_ai.evaluation.judge.model` | `claude-sonnet-4-6` |
| `gen_ai.evaluation.judge.provider` | `gateway` |
| `gen_ai.evaluation.reasoning` | short text (truncated to 500 chars) |
| `gen_ai.evaluation.passed` | `false` |
| `evallib.origin.trace_id` / `evallib.origin.span_id` | correlation back-pointers |

## 3. Regression events (orchestrator) — `enterprise.regression.detected`

| Attribute | Example |
|---|---|
| `enterprise.agent.id` | agent uuid |
| `enterprise.eval.id` | `refund_policy_compliance` |
| `enterprise.regression.baseline_score` | `0.9066` |
| `enterprise.regression.current_score` | `0.7615` |
| `enterprise.regression.delta` | `-0.1451` |
| `enterprise.regression.candidate_causes` | JSON string (ranked) |

## 4. Collector processing

Defined in `otel-collector/otel-collector-config.yaml`:

- **PII redaction** (`transform/pii_redaction`) — regex masking of emails, SSNs,
  credit-card patterns, and phone numbers across **both** span attributes and
  span-event attributes. POC-grade; production would use a dedicated detector.
- **Resource enrichment** — stamps `deployment.environment` + `service.namespace`.
- **Exporters** — Phoenix (OTLP), a file exporter (`otel-audit.jsonl`, for audit
  replay + AC-8 inspection), debug console, and commented-out Datadog/Splunk.

### Inspecting emitted events

```bash
grep gen_ai.evaluation.result   otel-collector/output/otel-audit.jsonl | tail -1 | jq .
grep enterprise.regression.detected otel-collector/output/otel-audit.jsonl | tail -1 | jq .
```

## Versioning policy

- Pin `arize-phoenix` / `arize-phoenix-evals` in each `pyproject.toml`.
- Treat the attribute tables above as the contract; update them and this doc on
  any GenAI semconv minor release, and re-verify downstream dashboards.

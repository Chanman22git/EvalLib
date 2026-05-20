# Mock Model Gateway

Stands in for the enterprise model gateway. It is the **single chokepoint** for
LLM calls: every call is proxied to a provider and emits an OpenTelemetry GenAI
span. It also publishes change events to the Governance API.

## Where it fits

```
agent → mock-gateway → provider (mock | anthropic)
              │
              └─ OTel GenAI span → otel-collector → Phoenix
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness |
| POST | `/v1/chat` | Proxy a chat completion; emits a GenAI span |
| POST | `/v1/change-events` | Synthesize + forward a change event (FR-GW-4) |

OpenAPI docs at `/docs` when running.

### `POST /v1/chat`

```json
{
  "messages": [{"role": "user", "content": "What is your refund policy?"}],
  "operation_name": "chat",
  "temperature": 0.2,
  "agent": {
    "agent_id": "agent-support-refund",
    "framework": "langgraph",
    "criticality": "critical",
    "data_classification": "restricted",
    "business_unit": "retail-banking"
  }
}
```

Returns the completion plus `trace_id` / `span_id` so callers (e.g. the eval
orchestrator) can correlate the eval back to the originating trace.

## OTel attributes emitted

GenAI semantic conventions (v1.37+): `gen_ai.operation.name`,
`gen_ai.provider.name`, `gen_ai.request.model`, `gen_ai.response.model`,
`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`,
`gen_ai.response.finish_reasons`.

Enterprise extensions: `enterprise.agent.id`, `enterprise.agent.framework`,
`enterprise.agent.criticality`, `enterprise.agent.data_classification`,
`enterprise.business_unit`.

When `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true`, prompt and
response content are attached as span events (`gen_ai.user.message`,
`gen_ai.choice`, …).

## LLM mode

- `LLM_MODE=mock` (default): deterministic, network-free. Judge-style prompts
  get a well-formed JSON verdict so the orchestrator's parse path is exercised.
- `LLM_MODE=anthropic`: real calls (needs `ANTHROPIC_API_KEY`).

## Test

```bash
pytest -q          # from this directory, or: make test-governance-style
```

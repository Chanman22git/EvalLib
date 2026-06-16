"""OpenTelemetry setup + GenAI semantic-convention helpers for the gateway.

Attribute names follow the OTel GenAI Semantic Conventions (v1.37+). Enterprise
extensions live under the `enterprise.*` namespace. See docs/otel-conventions.md.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import SpanKind, Status, StatusCode

from .config import settings
from .schemas import AgentContext, ChatRequest, ChatResponse, Message

# ── GenAI semantic-convention attribute keys ────────────────────────────────
GEN_AI_OPERATION_NAME = "gen_ai.operation.name"
GEN_AI_PROVIDER_NAME = "gen_ai.provider.name"
GEN_AI_REQUEST_MODEL = "gen_ai.request.model"
GEN_AI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
GEN_AI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
GEN_AI_RESPONSE_MODEL = "gen_ai.response.model"
GEN_AI_RESPONSE_FINISH_REASONS = "gen_ai.response.finish_reasons"
GEN_AI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GEN_AI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"

# ── Enterprise extension attribute keys ─────────────────────────────────────
ENTERPRISE_AGENT_ID = "enterprise.agent.id"
ENTERPRISE_AGENT_FRAMEWORK = "enterprise.agent.framework"
ENTERPRISE_AGENT_CRITICALITY = "enterprise.agent.criticality"
ENTERPRISE_AGENT_DATA_CLASSIFICATION = "enterprise.agent.data_classification"
ENTERPRISE_BUSINESS_UNIT = "enterprise.business_unit"

# Conversation/thread grouping. `session.id` is the key Phoenix uses to collapse
# a multi-turn conversation into one thread; mirrored under enterprise.* too.
SESSION_ID = "session.id"
ENTERPRISE_SESSION_ID = "enterprise.session.id"

_tracer: trace.Tracer | None = None


def init_tracing() -> trace.Tracer:
    """Initialise the global tracer provider once and return a tracer."""
    global _tracer
    if _tracer is not None:
        return _tracer

    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.namespace": settings.service_namespace,
            "deployment.environment": settings.deployment_environment,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
        )
    )
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("evallib.mock-gateway")
    return _tracer


def _agent_attributes(agent: AgentContext) -> dict[str, str]:
    return {
        ENTERPRISE_AGENT_ID: agent.agent_id,
        ENTERPRISE_AGENT_FRAMEWORK: agent.framework,
        ENTERPRISE_AGENT_CRITICALITY: agent.criticality.value,
        ENTERPRISE_AGENT_DATA_CLASSIFICATION: agent.data_classification.value,
        ENTERPRISE_BUSINESS_UNIT: agent.business_unit,
    }


def _capture_messages(span: trace.Span, messages: list[Message]) -> None:
    """Record prompt content as span events, per OTel GenAI spec.

    Only invoked when OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT is on.
    Content flows through the collector's PII redaction before reaching backends.
    """
    for msg in messages:
        event_name = {
            "system": "gen_ai.system.message",
            "user": "gen_ai.user.message",
            "assistant": "gen_ai.assistant.message",
        }.get(msg.role, "gen_ai.user.message")
        span.add_event(event_name, attributes={"content": msg.content, "role": msg.role})


@contextmanager
def gen_ai_span(req: ChatRequest, model: str) -> Iterator[trace.Span]:
    """Open a span for a gateway LLM call, pre-populated with request attributes.

    The caller fills in response attributes (model, tokens, finish reason) before
    the context exits. Yields the span so the caller can read its trace/span ids.
    """
    tracer = init_tracing()
    span_name = f"{req.operation_name} {model}"
    with tracer.start_as_current_span(span_name, kind=SpanKind.CLIENT) as span:
        span.set_attribute(GEN_AI_OPERATION_NAME, req.operation_name)
        span.set_attribute(GEN_AI_PROVIDER_NAME, req.provider)
        span.set_attribute(GEN_AI_REQUEST_MODEL, model)
        span.set_attribute(GEN_AI_REQUEST_TEMPERATURE, req.temperature)
        span.set_attribute(GEN_AI_REQUEST_MAX_TOKENS, req.max_tokens)
        if req.session_id:
            span.set_attribute(SESSION_ID, req.session_id)
            span.set_attribute(ENTERPRISE_SESSION_ID, req.session_id)
        for key, value in _agent_attributes(req.agent).items():
            span.set_attribute(key, value)
        if settings.otel_instrumentation_genai_capture_message_content:
            _capture_messages(span, req.messages)
        yield span


def record_response(span: trace.Span, resp: ChatResponse) -> None:
    span.set_attribute(GEN_AI_RESPONSE_MODEL, resp.model)
    span.set_attribute(GEN_AI_RESPONSE_FINISH_REASONS, [resp.finish_reason])
    span.set_attribute(GEN_AI_USAGE_INPUT_TOKENS, resp.usage.input_tokens)
    span.set_attribute(GEN_AI_USAGE_OUTPUT_TOKENS, resp.usage.output_tokens)
    if settings.otel_instrumentation_genai_capture_message_content:
        span.add_event(
            "gen_ai.choice",
            attributes={"content": resp.content, "finish_reason": resp.finish_reason},
        )
    span.set_status(Status(StatusCode.OK))


def record_error(span: trace.Span, exc: Exception) -> None:
    span.record_exception(exc)
    span.set_status(Status(StatusCode.ERROR, str(exc)))

"""Emit `gen_ai.evaluation.result` events (FR-EO-3) and self-telemetry (NFR-3).

Each eval result is emitted as a span named `evaluation <eval_id>` that carries a
Link back to the original trace/span, with a `gen_ai.evaluation.result` event and
GenAI-evaluation attributes. The collector's file exporter captures these so they
can be inspected per AC-8, and they fan out to Phoenix/Datadog/Splunk like any
other signal.
"""

from __future__ import annotations

import json

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import Link, NonRecordingSpan, SpanContext, TraceFlags

from .config import settings
from .schemas import EvalVerdict

EVAL_EVENT_NAME = "gen_ai.evaluation.result"
REGRESSION_EVENT_NAME = "enterprise.regression.detected"

_tracer: trace.Tracer | None = None


def init_tracing(app=None) -> trace.Tracer:
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
    _tracer = trace.get_tracer("evallib.eval-orchestrator")

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception:  # noqa: BLE001
            pass
    return _tracer


def _link_to_origin(trace_id: str, span_id: str | None) -> list[Link]:
    if not span_id:
        return []
    try:
        ctx = SpanContext(
            trace_id=int(trace_id, 16),
            span_id=int(span_id, 16),
            is_remote=True,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )
        return [Link(ctx)]
    except (ValueError, TypeError):
        return []


def emit_evaluation_result(v: EvalVerdict, judge_provider: str = "gateway") -> None:
    """Emit one eval verdict as an OTel event linked to the original span."""
    tracer = init_tracing()
    links = _link_to_origin(v.trace_id, v.span_id)
    with tracer.start_as_current_span(f"evaluation {v.eval_id}", links=links) as span:
        attributes = {
            "gen_ai.evaluation.name": v.eval_id,
            "gen_ai.evaluation.version": v.eval_version,
            "gen_ai.evaluation.verdict": v.verdict,
            "gen_ai.evaluation.score": v.score,
            "gen_ai.evaluation.judge.model": v.judge_model,
            "gen_ai.evaluation.judge.provider": judge_provider,
            "gen_ai.evaluation.reasoning": v.reasoning[:500],
            "gen_ai.evaluation.passed": v.passed,
            "evallib.origin.trace_id": v.trace_id,
            "evallib.origin.span_id": v.span_id or "",
        }
        for key, value in attributes.items():
            span.set_attribute(key, value)
        span.add_event(EVAL_EVENT_NAME, attributes=attributes)


def emit_regression_detected(
    *,
    agent_id: str,
    eval_id: str,
    baseline_score: float,
    current_score: float,
    delta: float,
    candidate_causes: list[dict],
) -> None:
    """Emit an `enterprise.regression.detected` OTel event (FR-RD-3)."""
    tracer = init_tracing()
    with tracer.start_as_current_span(f"regression {eval_id}") as span:
        attributes = {
            "enterprise.agent.id": agent_id,
            "enterprise.eval.id": eval_id,
            "enterprise.regression.baseline_score": baseline_score,
            "enterprise.regression.current_score": current_score,
            "enterprise.regression.delta": delta,
            "enterprise.regression.candidate_causes": json.dumps(candidate_causes),
        }
        for key, value in attributes.items():
            span.set_attribute(key, value)
        span.add_event(REGRESSION_EVENT_NAME, attributes=attributes)

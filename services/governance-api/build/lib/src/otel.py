"""Self-observability for the Governance API (NFR-3 — eat the dogfood)."""

from __future__ import annotations

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import settings

_initialised = False


def init_tracing(app=None) -> None:
    global _initialised
    if _initialised:
        return
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

    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception:  # noqa: BLE001 — instrumentation is best-effort in the POC
            pass
    _initialised = True

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from opentelemetry.trace import format_span_id, format_trace_id

from .change_events import publish_change_event
from .otel_instrumentation import gen_ai_span, init_tracing, record_error, record_response
from .providers import get_provider
from .schemas import (
    ChangeEventRequest,
    ChatRequest,
    ChatResponse,
    Usage,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_tracing()
    yield


app = FastAPI(
    title="EvalLib Mock Gateway",
    description="Mock enterprise model gateway: proxies LLM calls and emits OTel GenAI telemetry.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "mock-gateway"}


@app.post("/v1/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """Proxy a chat completion through the gateway, emitting an OTel GenAI span."""
    provider = get_provider()
    model = req.model or provider_default_model(req)

    with gen_ai_span(req, model) as span:
        try:
            result = await provider.complete(req, model)
        except Exception as exc:  # noqa: BLE001 — surface upstream failures as 502
            record_error(span, exc)
            raise HTTPException(status_code=502, detail=f"Upstream provider error: {exc}") from exc

        ctx = span.get_span_context()
        response = ChatResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            model=result.model,
            provider=provider.name,
            content=result.content,
            finish_reason=result.finish_reason,
            usage=Usage(input_tokens=result.input_tokens, output_tokens=result.output_tokens),
            trace_id=format_trace_id(ctx.trace_id),
            span_id=format_span_id(ctx.span_id),
        )
        record_response(span, response)
        return response


@app.post("/v1/change-events")
async def change_event(event: ChangeEventRequest) -> dict:
    """Synthesize a gateway change event and forward it to the Governance API."""
    return await publish_change_event(event)


def provider_default_model(req: ChatRequest) -> str:
    from .config import settings

    return settings.gateway_default_model

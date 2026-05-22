from __future__ import annotations

import httpx

from ..config import settings
from ..schemas import ChatRequest
from .base import ProviderResult

_FINISH_REASON_MAP = {
    "end_turn": "stop",
    "max_tokens": "length",
    "stop_sequence": "stop",
    "tool_use": "tool_calls",
}


class AnthropicProvider:
    """Real Anthropic provider. Active only when LLM_MODE=anthropic.

    Calls the Messages REST API directly via httpx rather than the SDK, so the
    gateway is resilient to SDK/API version drift, and so we only send the
    `system` field when it is actually present (the API rejects a null system).
    """

    name = "anthropic"

    def __init__(self) -> None:
        self._api_key = settings.anthropic_api_key
        self._base_url = settings.anthropic_base_url.rstrip("/")

    async def complete(self, req: ChatRequest, model: str) -> ProviderResult:
        # Resolve placeholder model ids to the configured real model.
        model_to_call = settings.anthropic_model or model
        system = "\n".join(m.content for m in req.messages if m.role == "system")
        body: dict = {
            "model": model_to_call,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "messages": [
                {"role": m.role, "content": m.content}
                for m in req.messages
                if m.role in ("user", "assistant")
            ],
        }
        if system:
            body["system"] = system

        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self._base_url}/v1/messages", json=body, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"Error code: {resp.status_code} - {resp.text}")

        data = resp.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        usage = data.get("usage", {})
        return ProviderResult(
            content=text,
            model=data.get("model", model_to_call),
            finish_reason=_FINISH_REASON_MAP.get(data.get("stop_reason") or "", "stop"),
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
        )

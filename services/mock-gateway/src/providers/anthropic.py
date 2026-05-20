from __future__ import annotations

from anthropic import AsyncAnthropic

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
    """Real Anthropic provider. Active only when LLM_MODE=anthropic."""

    name = "anthropic"

    def __init__(self) -> None:
        self._client = AsyncAnthropic(
            api_key=settings.anthropic_api_key,
            base_url=settings.anthropic_base_url,
        )

    async def complete(self, req: ChatRequest, model: str) -> ProviderResult:
        # Resolve placeholder model ids to the configured real model.
        model_to_call = settings.anthropic_model or model
        system = "\n".join(m.content for m in req.messages if m.role == "system")
        chat = [
            {"role": m.role, "content": m.content}
            for m in req.messages
            if m.role in ("user", "assistant")
        ]
        resp = await self._client.messages.create(
            model=model_to_call,
            system=system or None,
            messages=chat,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return ProviderResult(
            content=text,
            model=resp.model,
            finish_reason=_FINISH_REASON_MAP.get(resp.stop_reason or "", "stop"),
            input_tokens=resp.usage.input_tokens,
            output_tokens=resp.usage.output_tokens,
        )

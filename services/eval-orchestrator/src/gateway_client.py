from __future__ import annotations

import httpx

from .config import settings


class GatewayClient:
    """Calls the judge LLM *through the model gateway*.

    All LLM traffic — including eval judges — funnels through the gateway so it
    stays the single observable chokepoint (architecture decision). The gateway's
    mock provider returns a well-formed JSON verdict for judge-style prompts, so
    the full parse/validate path runs without a real model.
    """

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or settings.gateway_url).rstrip("/")

    async def judge(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
        agent_context: dict,
    ) -> dict:
        payload = {
            "operation_name": "chat",
            "model": model,
            "temperature": temperature,
            "max_tokens": 1024,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "agent": agent_context,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self._base}/v1/chat", json=payload)
            resp.raise_for_status()
            return resp.json()

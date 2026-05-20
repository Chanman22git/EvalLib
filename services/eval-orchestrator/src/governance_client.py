from __future__ import annotations

from typing import Any

import httpx

from .config import settings


class GovernanceClient:
    """Thin HTTP client for the Governance API."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base = (base_url or settings.governance_api_url).rstrip("/")

    async def _get(self, path: str, params: dict | None = None) -> Any:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self._base}{path}", params=params)
            resp.raise_for_status()
            return resp.json()

    async def _post(self, path: str, json: dict) -> Any:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self._base}{path}", json=json)
            resp.raise_for_status()
            return resp.json()

    async def resolve_eval(self, eval_id: str, version: str | None = None) -> dict | None:
        """Find an eval by its string id (+optional version), preferring approved ones."""
        evals = await self._get("/evals")
        matches = [e for e in evals if e["eval_id"] == eval_id]
        if version is not None:
            matches = [e for e in matches if e["version"] == version]
        if not matches:
            return None
        approved = [e for e in matches if e["review_status"] == "approved"]
        pool = approved or matches
        # Newest by created_at.
        return sorted(pool, key=lambda e: e["created_at"], reverse=True)[0]

    async def get_agent_mappings(self, agent_id: str | None = None) -> list[dict]:
        params = {"agent_id": agent_id} if agent_id else None
        return await self._get("/eval-agent-mapping", params=params)

    async def get_eval_by_pk(self, eval_pk: str) -> dict:
        return await self._get(f"/evals/{eval_pk}")

    async def list_agents(self) -> list[dict]:
        return await self._get("/agents")

    async def post_eval_result(self, payload: dict) -> dict:
        return await self._post("/eval-results", payload)

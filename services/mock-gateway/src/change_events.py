"""Publish gateway change events to the Governance API (FR-GW-4).

The real enterprise gateway emits change events whenever model routing, prompt
templates, tool definitions, or agent lifecycle state change. The mock gateway
exposes admin endpoints that synthesize these and forwards them to the
Governance API. Forwarding is best-effort: if the Governance API is unavailable
(e.g. Phase A standalone), the event is logged and the call still succeeds.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx

from .config import settings
from .schemas import ChangeEventRequest

logger = logging.getLogger("mock-gateway.change_events")


async def publish_change_event(event: ChangeEventRequest) -> dict:
    payload = {
        "event_id": str(uuid.uuid4()),
        "event_type": event.event_type.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent_id": event.agent_id,
        "actor": event.actor,
        "before": event.before,
        "after": event.after,
        "reason": event.reason,
    }
    url = f"{settings.governance_api_url}/change-events"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        payload["forwarded"] = True
    except (httpx.HTTPError, httpx.ConnectError) as exc:
        logger.warning("Could not forward change event to Governance API: %s", exc)
        payload["forwarded"] = False
    return payload

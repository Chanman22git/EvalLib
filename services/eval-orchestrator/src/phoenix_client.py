"""Phoenix integration: fetch trace I/O and log eval annotations.

All Phoenix calls are best-effort and guarded. The authoritative outputs of an
eval are the OTel event and the Governance Store mirror; the Phoenix annotation
is supplementary, so a Phoenix API mismatch never fails an eval.
"""

from __future__ import annotations

import logging

from .config import settings

logger = logging.getLogger("eval-orchestrator.phoenix")

try:
    from phoenix.client import Client as _PhoenixClient
except Exception:  # noqa: BLE001
    _PhoenixClient = None


def _client():
    if _PhoenixClient is None:
        return None
    try:
        return _PhoenixClient(base_url=settings.phoenix_base_url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Phoenix client unavailable: %s", exc)
        return None


def fetch_trace_io(trace_id: str) -> tuple[str | None, str | None]:
    """Return (input, output) for a trace's root LLM span, if reachable."""
    client = _client()
    if client is None:
        return None, None
    try:
        spans = client.spans.get_spans(
            project_identifier=settings.phoenix_project, trace_ids=[trace_id], limit=50
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not fetch spans for trace %s: %s", trace_id, exc)
        return None, None

    for span in spans:
        attrs = (span.get("attributes") or {}) if isinstance(span, dict) else {}
        gen_ai = attrs.get("gen_ai", {}) if isinstance(attrs, dict) else {}
        in_val = (gen_ai.get("prompt") if isinstance(gen_ai, dict) else None) or attrs.get("input")
        out_val = (gen_ai.get("completion") if isinstance(gen_ai, dict) else None) or attrs.get("output")
        if in_val or out_val:
            return (str(in_val) if in_val else None, str(out_val) if out_val else None)
    return None, None


def annotate_span(
    *, span_id: str, eval_id: str, label: str, score: float, explanation: str, judge_model: str
) -> bool:
    """Log an eval result back to Phoenix as a span annotation (FR-EO-2 step 8)."""
    client = _client()
    if client is None or not span_id:
        return False
    try:
        client.spans.add_span_annotation(
            span_id=span_id,
            annotation_name=eval_id,
            annotator_kind="LLM",
            label=label,
            score=score,
            explanation=explanation,
            metadata={"judge_model": judge_model},
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not annotate span %s in Phoenix: %s", span_id, exc)
        return False

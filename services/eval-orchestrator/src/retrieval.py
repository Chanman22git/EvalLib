"""Mock retrieval (FR-EO-2 step 3).

The POC retrieves from a small in-memory document store keyed by collection. A
production deployment would swap this for a real vector store / KB. The eval's
`retrieval_config` selects a collection and top_k.
"""

from __future__ import annotations

# Tiny knowledge base used by retrieval-backed evals (e.g. refund policy).
_DOCS: dict[str, list[str]] = {
    "refund_policy": [
        "Refunds are available within 30 days of purchase with a valid receipt.",
        "Digital goods are non-refundable once downloaded.",
        "Refunds are issued to the original payment method within 5-7 business days.",
    ],
    "brand_voice": [
        "Always address customers respectfully and avoid slang.",
        "Use plain language; avoid unexplained financial jargon.",
    ],
    "default": [
        "No additional context is configured for this collection.",
    ],
}


def retrieve(retrieval_config: dict | None, query: str) -> list[str]:
    if not retrieval_config:
        return []
    collection = retrieval_config.get("collection", "default")
    top_k = int(retrieval_config.get("top_k", 3))
    docs = _DOCS.get(collection, _DOCS["default"])
    return docs[:top_k]

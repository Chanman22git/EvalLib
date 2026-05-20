"""Retrieval over the policy knowledge base (FR-EO-2 step 3).

Loads documents from `KB_DIR` (a folder of `.md`/`.txt` files mounted into the
container), chunks them on blank lines, and ranks chunks against the query with a
lightweight lexical (term-overlap) scorer — no embedding dependency, fully
offline, deterministic. The *same* KB also grounds the agent (see
`scripts/policy_agent.py`), so the judge grades answers against the exact text the
agent was given.

If a collection's document is not present, a small built-in fallback is used so
unit tests and a bare checkout still work.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from pathlib import Path

_STOPWORDS = {
    "the", "a", "an", "is", "are", "to", "of", "for", "and", "or", "in", "on",
    "i", "my", "can", "do", "does", "how", "what", "it", "this", "that", "you",
}

# Built-in fallback used when a KB document is not found on disk.
_FALLBACK: dict[str, list[str]] = {
    "refund_policy": [
        "Refunds are available within 30 days of purchase with a valid receipt.",
        "Digital goods are non-refundable once downloaded.",
        "Refunds are issued to the original payment method within 5-7 business days.",
    ],
    "brand_voice": [
        "Always address customers respectfully and avoid slang.",
        "Use plain language; avoid unexplained financial jargon.",
    ],
    "default": ["No additional context is configured for this collection."],
}


def _kb_dir() -> Path:
    return Path(os.getenv("KB_DIR", "kb"))


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS}


@lru_cache(maxsize=16)
def _chunks_for(collection: str) -> tuple[str, ...]:
    """Load + chunk a collection's document, falling back to the built-in text."""
    kb_dir = _kb_dir()
    for ext in (".md", ".txt"):
        path = kb_dir / f"{collection}{ext}"
        if path.exists():
            raw = path.read_text(encoding="utf-8")
            chunks = [c.strip() for c in re.split(r"\n\s*\n", raw) if c.strip()]
            # Drop pure-heading lines so chunks carry substance.
            chunks = [c for c in chunks if not re.fullmatch(r"#+\s.*", c)]
            if chunks:
                return tuple(chunks)
    return tuple(_FALLBACK.get(collection, _FALLBACK["default"]))


def retrieve(retrieval_config: dict | None, query: str) -> list[str]:
    if not retrieval_config:
        return []
    collection = retrieval_config.get("collection", "default")
    top_k = int(retrieval_config.get("top_k", 3))
    chunks = _chunks_for(collection)

    q = _tokens(query)
    if not q:
        return list(chunks[:top_k])

    scored = sorted(
        chunks,
        key=lambda c: len(q & _tokens(c)),
        reverse=True,
    )
    # Keep only chunks with at least one overlapping term; fall back to first chunks.
    relevant = [c for c in scored if q & _tokens(c)]
    return (relevant or list(chunks))[:top_k]

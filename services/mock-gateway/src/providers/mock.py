from __future__ import annotations

import hashlib
import json
import re

from ..schemas import ChatRequest
from .base import ProviderResult

# Heuristic: judge prompts ask for a JSON object containing a verdict + score.
_JUDGE_HINT = re.compile(r"verdict|json|score", re.IGNORECASE)
_VERDICTS = ["compliant", "non_compliant", "ambiguous"]

# Agents that ground answers put retrieved passages after this marker (see
# scripts/policy_agent.py). In mock mode we quote them so the answer is visibly
# grounded even without a real model.
_CONTEXT_MARKER = re.compile(r"policy context:\s*(.+)", re.IGNORECASE | re.DOTALL)
_SENTENCE = re.compile(r"[^.!?\n]+[.!?]")


def _extract_context(messages) -> str:
    """Pull the retrieved-context block from the system message (only)."""
    for m in messages:
        if m.role == "system":
            match = _CONTEXT_MARKER.search(m.content)
            if match:
                return match.group(1)
    return ""


def _estimate_tokens(text: str) -> int:
    # ~4 chars per token is a serviceable POC approximation.
    return max(1, len(text) // 4)


def _grounded_answer(context: str, question: str) -> str:
    """Compose a grounded-looking answer by quoting the most relevant context
    sentence (the one sharing the most words with the question)."""
    sentences = [s.strip() for s in _SENTENCE.findall(context) if s.strip()]
    if not sentences:
        sentences = [context.strip()[:200]] if context.strip() else []
    if not sentences:
        return "I don't see anything in the policy that covers that, so I'd escalate."
    q_words = {w for w in re.findall(r"[a-z0-9]+", question.lower()) if len(w) > 3}
    best = max(sentences, key=lambda s: len({w for w in re.findall(r"[a-z0-9]+", s.lower())} & q_words))
    return (
        f"Per the policy: {best} "
        "(mock grounded answer — set LLM_MODE=anthropic for a real model response.)"
    )


class MockProvider:
    """Deterministic, network-free provider for local development and CI.

    Returns canned-but-plausible text for ordinary chat, and a well-formed JSON
    verdict when the prompt looks like an LLM-as-judge request — so the eval
    orchestrator can exercise its full parse/validate path without a real LLM.
    """

    name = "mock"

    async def complete(self, req: ChatRequest, model: str) -> ProviderResult:
        last_user = next(
            (m.content for m in reversed(req.messages) if m.role == "user"),
            "",
        )
        full_prompt = " ".join(m.content for m in req.messages)
        digest = hashlib.sha256(full_prompt.encode()).hexdigest()

        if _JUDGE_HINT.search(full_prompt):
            # Deterministically pick a verdict from the prompt hash.
            verdict = _VERDICTS[int(digest[:8], 16) % len(_VERDICTS)]
            score = {"compliant": 0.95, "non_compliant": 0.15, "ambiguous": 0.55}[verdict]
            content = json.dumps(
                {
                    "verdict": verdict,
                    "score": score,
                    "reasoning": f"[mock judge] Deterministic verdict derived from prompt hash {digest[:8]}.",
                    "passed": verdict == "compliant",
                }
            )
        else:
            context = _extract_context(req.messages)
            if context:
                # Grounded chat: quote the retrieved policy context.
                content = _grounded_answer(context, last_user)
            else:
                content = (
                    f"[mock:{model}] Acknowledged: \"{last_user[:120]}\". "
                    "This is a deterministic mock response; set LLM_MODE=anthropic for real calls."
                )

        return ProviderResult(
            content=content,
            model=model,
            finish_reason="stop",
            input_tokens=_estimate_tokens(full_prompt),
            output_tokens=_estimate_tokens(content),
        )

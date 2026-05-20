from __future__ import annotations

from pathlib import Path

import pytest

from src import retrieval

# Repo-root kb/ relative to this test file: services/eval-orchestrator/tests → repo root
KB_DIR = Path(__file__).resolve().parents[3] / "kb"


@pytest.fixture()
def use_real_kb(monkeypatch):
    monkeypatch.setenv("KB_DIR", str(KB_DIR))
    retrieval._chunks_for.cache_clear()
    yield
    retrieval._chunks_for.cache_clear()


def test_retrieve_grounds_in_real_policy_doc(use_real_kb):
    assert KB_DIR.exists(), "sample kb/ doc should exist"
    chunks = retrieval.retrieve({"collection": "refund_policy", "top_k": 3}, "Can I get a refund after 25 days?")
    joined = "\n".join(chunks).lower()
    assert chunks, "expected at least one retrieved chunk"
    assert "30 days" in joined  # the eligibility window text was retrieved


def test_retrieve_ranks_relevant_chunk_first(use_real_kb):
    chunks = retrieval.retrieve({"collection": "refund_policy", "top_k": 1}, "digital ebook download refund")
    assert len(chunks) == 1
    assert "digital" in chunks[0].lower()


def test_retrieve_falls_back_when_doc_missing(monkeypatch):
    monkeypatch.setenv("KB_DIR", "/nonexistent-kb-path")
    retrieval._chunks_for.cache_clear()
    chunks = retrieval.retrieve({"collection": "refund_policy", "top_k": 2}, "refund")
    assert any("30 days" in c for c in chunks)  # built-in fallback still works
    retrieval._chunks_for.cache_clear()


def test_no_config_returns_empty():
    assert retrieval.retrieve(None, "anything") == []

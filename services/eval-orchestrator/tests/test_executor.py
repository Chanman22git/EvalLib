from __future__ import annotations

import json

import pytest

from src.executor import EvalNotRunnable, _parse_judge_output, _render_prompt, assert_runnable
from src.schemas import TraceRef


def _eval_def(**overrides):
    base = {
        "eval_id": "refund_policy_compliance",
        "version": "1.0.0",
        "review_status": "approved",
        "criterion_description": "Must comply with refund policy.",
        "prompt_template": "Criterion: {criterion}\nInput: {input}\nOutput: {output}\nContext: {context}",
        "judge_config": {"model": "claude-sonnet-4-6", "temperature": 0.0},
        "output_schema": {"required": ["verdict", "score"]},
        "retrieval_config": {"collection": "refund_policy", "top_k": 2},
    }
    base.update(overrides)
    return base


def test_assert_runnable_rejects_non_approved():
    with pytest.raises(EvalNotRunnable):
        assert_runnable(_eval_def(review_status="draft"))


def test_assert_runnable_rejects_expired():
    with pytest.raises(EvalNotRunnable):
        assert_runnable(_eval_def(expires_at="2000-01-01T00:00:00+00:00"))


def test_render_prompt_includes_retrieved_context():
    ref = TraceRef(trace_id="t1", input="Can I get a refund?", output="Yes, within 30 days.")
    from src.retrieval import retrieve

    ctx = retrieve(_eval_def()["retrieval_config"], ref.input)
    prompt = _render_prompt(_eval_def(), ref, ctx)
    assert "refund" in prompt.lower()
    assert "30 days" in prompt


def test_parse_judge_output_happy():
    content = json.dumps({"verdict": "compliant", "score": 0.95, "reasoning": "ok", "passed": True})
    out = _parse_judge_output(content, {"required": ["verdict", "score"]})
    assert out.verdict == "compliant"
    assert out.score == 0.95
    assert out.passed is True


def test_parse_judge_output_infers_passed_from_verdict():
    content = json.dumps({"verdict": "non_compliant", "score": 0.1})
    out = _parse_judge_output(content, {"required": ["verdict", "score"]})
    assert out.passed is False


def test_parse_judge_output_missing_key_raises():
    with pytest.raises(ValueError):
        _parse_judge_output(json.dumps({"score": 0.5}), {"required": ["verdict", "score"]})


def test_parse_judge_output_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        _parse_judge_output("not json", {"required": ["verdict"]})

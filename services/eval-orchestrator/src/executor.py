"""Eval execution pipeline (FR-EO-2).

For one (eval, trace) pair:
  1. resolve trace I/O (inline or from Phoenix)
  2. verify the eval is approved and not expired
  3. retrieve context if the eval has retrieval_config
  4. render the judge prompt (via arize-phoenix-evals PromptTemplate)
  5. call the judge LLM through the gateway
  6. parse + validate the output; retry once with a stricter instruction
  7. persist to the Governance Store, emit the OTel event, annotate Phoenix
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from phoenix.evals import PromptTemplate

from . import phoenix_client
from .gateway_client import GatewayClient
from .governance_client import GovernanceClient
from .otel_emitter import emit_evaluation_result
from .retrieval import retrieve
from .schemas import EvalVerdict, JudgeOutput, TraceRef

logger = logging.getLogger("eval-orchestrator.executor")

PASS_VERDICTS = {"compliant", "correct", "grounded", "pass", "passed", "helpful", "safe", "yes"}

_STRICT_SUFFIX = (
    "\n\nIMPORTANT: Respond with ONLY a single JSON object and no prose, e.g. "
    '{"verdict": "compliant", "score": 0.9, "reasoning": "...", "passed": true}.'
)


class EvalNotRunnable(ValueError):
    """Raised when an eval cannot be run (not approved, expired, missing)."""


def assert_runnable(eval_def: dict) -> None:
    if eval_def["review_status"] != "approved":
        raise EvalNotRunnable(
            f"Eval {eval_def['eval_id']} is '{eval_def['review_status']}', not 'approved'."
        )
    expires_at = eval_def.get("expires_at")
    if expires_at:
        exp = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        if exp < datetime.now(timezone.utc):
            raise EvalNotRunnable(f"Eval {eval_def['eval_id']} expired at {expires_at}.")


def _default_template() -> str:
    return (
        "You are an impartial evaluator. Criterion: {criterion}\n"
        "Context: {context}\n"
        "Agent input: {input}\n"
        "Agent output: {output}\n"
        "Return a JSON object with keys verdict (string), score (0-1 float), "
        "reasoning (string), passed (boolean)."
    )


def _render_prompt(eval_def: dict, ref: TraceRef, context: list[str]) -> str:
    template_text = eval_def.get("prompt_template") or _default_template()
    template = PromptTemplate(template_text)
    values: dict[str, str] = {
        "input": ref.input or "",
        "output": ref.output or "",
        "context": "\n".join(context),
        "criterion": eval_def.get("criterion_description", ""),
    }
    # Supply empty strings for any template variables we don't recognise.
    for var in getattr(template, "variables", []):
        values.setdefault(var, "")
    return str(template.format(values))


def _parse_judge_output(content: str, output_schema: dict) -> JudgeOutput:
    """Parse + validate judge output against the eval's output schema."""
    data = json.loads(content)
    required = output_schema.get("required", ["verdict", "score"])
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Judge output missing required keys: {missing}")
    verdict = str(data["verdict"]).lower()
    score = float(data.get("score", 0.0))
    passed = data.get("passed")
    if passed is None:
        passed = verdict in PASS_VERDICTS
    return JudgeOutput(
        verdict=verdict,
        score=score,
        reasoning=str(data.get("reasoning", "")),
        passed=bool(passed),
    )


class Executor:
    def __init__(self, governance: GovernanceClient | None = None, gateway: GatewayClient | None = None) -> None:
        self.governance = governance or GovernanceClient()
        self.gateway = gateway or GatewayClient()

    async def run(self, eval_def: dict, ref: TraceRef, judge_model: str | None = None) -> EvalVerdict:
        assert_runnable(eval_def)

        # 1. Resolve trace I/O.
        if ref.input is None and ref.output is None:
            ref.input, ref.output = phoenix_client.fetch_trace_io(ref.trace_id)

        # 2. Retrieval.
        context = retrieve(eval_def.get("retrieval_config"), ref.input or "")

        # 3. Render prompt.
        user_prompt = _render_prompt(eval_def, ref, context)
        judge_cfg = eval_def.get("judge_config") or {}
        model = judge_model or judge_cfg.get("model") or "claude-sonnet-4-6"
        temperature = float(judge_cfg.get("temperature", 0.0))
        agent_context = {
            "agent_id": str(ref.agent_id) if ref.agent_id else "eval-judge",
            "framework": "evallib-judge",
            "criticality": "low",
            "data_classification": "internal",
            "business_unit": "governance",
        }
        output_schema = eval_def.get("output_schema") or {}

        # 4-6. Judge call with one stricter retry on parse failure.
        verdict_obj, error = await self._judge_with_retry(
            system_prompt="You are an LLM-as-judge evaluator. Respond in JSON.",
            user_prompt=user_prompt,
            model=model,
            temperature=temperature,
            agent_context=agent_context,
            output_schema=output_schema,
        )

        result = EvalVerdict(
            trace_id=ref.trace_id,
            span_id=ref.span_id,
            session_id=ref.session_id,
            eval_id=eval_def["eval_id"],
            eval_version=eval_def["version"],
            verdict=verdict_obj.verdict if verdict_obj else "judge_error",
            score=verdict_obj.score if verdict_obj else 0.0,
            reasoning=verdict_obj.reasoning if verdict_obj else (error or "unknown error"),
            judge_model=model,
            passed=bool(verdict_obj.passed) if verdict_obj else False,
            error=error,
        )

        # 7. Persist + emit + annotate (Phoenix is best-effort).
        await self._persist(result, ref)
        emit_evaluation_result(result)
        phoenix_client.annotate_span(
            span_id=ref.span_id or "",
            eval_id=result.eval_id,
            label=result.verdict,
            score=result.score,
            explanation=result.reasoning,
            judge_model=result.judge_model,
        )
        return result

    async def _judge_with_retry(
        self, *, system_prompt, user_prompt, model, temperature, agent_context, output_schema
    ) -> tuple[JudgeOutput | None, str | None]:
        for attempt in range(2):
            prompt = user_prompt if attempt == 0 else user_prompt + _STRICT_SUFFIX
            try:
                resp = await self.gateway.judge(
                    system_prompt=system_prompt,
                    user_prompt=prompt,
                    model=model,
                    temperature=temperature,
                    agent_context=agent_context,
                )
                return _parse_judge_output(resp["content"], output_schema), None
            except (json.JSONDecodeError, ValueError, KeyError) as exc:
                last_error = f"parse failure on attempt {attempt + 1}: {exc}"
                logger.warning(last_error)
            except Exception as exc:  # noqa: BLE001 — gateway/transport failure
                return None, f"judge call failed: {exc}"
        return None, last_error

    async def _persist(self, result: EvalVerdict, ref: TraceRef) -> None:
        try:
            await self.governance.post_eval_result(
                {
                    "trace_id": result.trace_id,
                    "span_id": result.span_id,
                    "session_id": result.session_id,
                    "eval_id": result.eval_id,
                    "eval_version": result.eval_version,
                    "verdict": result.verdict,
                    "score": result.score,
                    "reasoning": result.reasoning,
                    "judge_model": result.judge_model,
                    "agent_id": str(ref.agent_id) if ref.agent_id else None,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not persist eval result to Governance: %s", exc)

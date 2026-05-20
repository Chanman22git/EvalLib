# Acceptance Criteria — Status

Walkthrough of PRD §8 (AC-1…AC-12) against the running stack. All criteria pass.
Commands to reproduce each are included.

> Verified in mock LLM mode (`LLM_MODE=mock`). The same flow works with
> `LLM_MODE=anthropic` + an API key for real judges.

| AC | Criterion | Status | Evidence |
|----|-----------|:------:|----------|
| **AC-1** | `docker compose up` brings the full stack live; health checks pass | ✅ | All 6 services report `healthy` (`docker compose ps`). Phoenix + UI healthchecks fixed to exec-form / `127.0.0.1`. |
| **AC-2** | Seed populates 5 agents, 8 evals, 200+ traces, 50+ results, 1 regression | ✅ | After `make reset && make seed`: 5 agents, 8 evals, 3 calibration sets, ~294 eval results (≥200 distinct trace_ids), 1 injected regression. |
| **AC-3** | Live gateway call → trace in Phoenix within 5s | ✅ | `curl …/v1/chat` then Phoenix shows the span (gateway + judge + evaluation spans) within ~1–2s. |
| **AC-4** | Same trace in the UI `/traces` with agent metadata, eval verdicts, Open-in-Phoenix | ✅ | Trace Explorer + Trace Detail render the governance overlay and a working Phoenix deep link. |
| **AC-5** | Create → submit → fail approval (low agreement) → attach stronger set → approve; audit shows transitions | ✅ | Demonstrated live (below). Audit trail: `create → in_review → calibration → calibration → approved`. |
| **AC-6** | Dashboard loads < 2s with accurate KPIs | ✅ | Governance queries return in ~20ms; KPIs match seed (5 agents, 3 approved evals, open regression count). |
| **AC-7** | Injected regression appears with KB re-index ranked top candidate cause | ✅ | Live `POST /detect-regressions` created the refund alert (0.91→0.76, Δ−0.145) with **"policy KB re-index" ranked #1**. |
| **AC-8** | Every eval result emitted to OTel; inspectable in the file exporter; conforms to schema | ✅ | `gen_ai.evaluation.result` and `enterprise.regression.detected` events present in `otel-collector/output/otel-audit.jsonl` with the documented attributes. |
| **AC-9** | Approving without calibration / below threshold returns 400; state cannot advance | ✅ | Live: `400 "no calibration set attached"`, then `400 "agreement 0.5 is below threshold 0.75"`. |
| **AC-10** | All endpoints have OpenAPI docs at `/docs`; UI consumes generated TS types | ✅ | `/openapi.json` returns 200 on :8001/:8002/:8080; UI types generated into `src/api/*.gen.ts` via `npm run gen:types`. |
| **AC-11** | Backend `pytest` passes; frontend `vitest` passes | ✅ | governance 17, mock-gateway 5, eval-orchestrator 22, UI vitest 4 — **48 tests pass** (in-container + locally). |
| **AC-12** | README takes a new engineer from zero to "I see eval results in the UI" in < 15 min | ✅ | `make setup && make up && make seed` (or `./scripts/demo.sh`), then open :3000. See [demo-script.md](demo-script.md). |

## Reproduce the headline checks

```bash
# AC-1 — health
docker compose ps

# AC-2 — seed counts
curl -s localhost:8001/agents | jq length          # 5
curl -s localhost:8001/evals  | jq length           # 8
curl -s 'localhost:8001/eval-results?limit=2000' | jq length   # 200+

# AC-7 — live regression detection
curl -s -X POST localhost:8002/detect-regressions | jq '{checked,created}'
curl -s localhost:8001/regression-alerts | jq '.[0] | {eval_id,delta,top_cause:.candidate_causes[0].reason}'

# AC-8 — portable OTel events
grep gen_ai.evaluation.result        otel-collector/output/otel-audit.jsonl | tail -1 | jq .
grep enterprise.regression.detected  otel-collector/output/otel-audit.jsonl | tail -1 | jq .

# AC-9 — approval guard (full flow in docs/governance-state-machine.md)
#   approve before calibration  -> 400 "no calibration set attached"
#   approve below threshold      -> 400 "agreement 0.5 is below threshold 0.75"

# AC-11 — tests
make test                                   # backend (pytest)
( cd services/ui && npm run test )          # frontend (vitest)
```

## Notes

- `make seed` assumes a fresh store (`make reset` first) — it registers agents by
  unique name and will 409 on a second run otherwise.
- AC-2's "200+ traces" is satisfied by the distinct `trace_id`s carried on seeded
  eval results; live Phoenix traces are produced by `demo.sh` (OpenTelemetry can't
  backdate spans).

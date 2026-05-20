# Demo Script

A 5-minute walkthrough that lands with all three audiences — engineering, risk &
compliance, and leadership.

## 0. Bring it up

```bash
make setup           # creates .env (mock LLM mode by default)
make up              # build + start the full stack
make seed            # populate demo data
# …or do all of the above plus a live eval in one shot:
./scripts/demo.sh
```

URLs: **UI** http://localhost:3000 · **Phoenix** http://localhost:6006 ·
**Governance API** http://localhost:8001/docs · **Orchestrator** http://localhost:8002/docs

> Mock mode needs no API key. For real judges: set `LLM_MODE=anthropic` and
> `ANTHROPIC_API_KEY` in `.env`, then `make up`.

## 1. Leadership — the Dashboard (`/`)

Open the UI. The dashboard shows the KPIs (active agents, approved evals, evals
run in 24h, open regressions), a 7-day aggregate pass-rate trend, and recent
regression alerts + change events. One regression is already visible.

## 2. Engineering — trace → eval (live)

Send a call through the gateway and evaluate it:

```bash
CHAT=$(curl -s localhost:8080/v1/chat -H 'content-type: application/json' -d '{
  "messages":[{"role":"user","content":"A customer wants a refund after 25 days."}],
  "agent":{"agent_id":"customer-support-refund","framework":"langgraph",
           "criticality":"critical","data_classification":"restricted",
           "business_unit":"retail-banking"}}')
TRACE=$(echo "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["trace_id"])')
SPAN=$(echo  "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["span_id"])')

curl -s localhost:8002/run-eval -H 'content-type: application/json' -d "{
  \"eval_id\":\"refund_policy_compliance\",
  \"traces\":[{\"trace_id\":\"$TRACE\",\"span_id\":\"$SPAN\",
               \"input\":\"refund after 25 days?\",\"output\":\"Yes, within 30 days you qualify.\"}]}" | jq .
```

- The trace appears in **Phoenix** (http://localhost:6006) within seconds.
- It appears in the UI under **Traces** → click it → see the eval verdict,
  reasoning, judge model, and an "Open in Phoenix" deep link.

## 3. Risk & compliance — the governance workflow (`/evals`)

Walk the eval lifecycle (this is AC-5):

1. **Create New Eval** → it starts as `draft`.
2. On its detail page: **Submit for review** → `in_review`.
3. **Approve** → **fails** (no calibration / agreement below threshold) with a
   clear message — governance is enforced.
4. Attach a strong calibration set → **Run agreement test** → agreement clears
   the threshold.
5. **Approve** → succeeds. The **Audit trail** on the page shows every
   transition with actor and timestamp.

## 4. Regression + root cause (`/regressions`)

The seeded `refund_policy_compliance` regression on the refund agent shows a
~15% drop. Its **candidate causes** are ranked, with the **"policy KB re-index"**
change event at #1. Trigger the live detector to show it is computed, not
hard-coded:

```bash
curl -s -X POST localhost:8002/detect-regressions | jq '{checked,created}'
```

The `/changes` page shows the same KB re-index event with a before/after diff.

## 5. Evidence (`/governance`)

The Governance page reports coverage metrics and offers **CSV exports** (agent
inventory, eval inventory, eval-result log). Toggle **Regulator view** for the
simplified, evidence-focused layout.

## 6. Portability (AC-8)

Every eval/regression result is also emitted as an OTel event — inspect the
collector's file exporter:

```bash
grep gen_ai.evaluation.result       otel-collector/output/otel-audit.jsonl | tail -1 | jq .
grep enterprise.regression.detected otel-collector/output/otel-audit.jsonl | tail -1 | jq .
```

## Reset

```bash
make reset    # stop the stack and wipe volumes + collector output
```

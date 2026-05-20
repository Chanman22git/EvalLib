#!/usr/bin/env bash
# EvalLib end-to-end demo (FR-SD-2).
#   up → seed → live gateway call → eval that call → print URLs.
set -euo pipefail

cd "$(dirname "$0")/.."

GATEWAY=http://localhost:8080
GOVERNANCE=http://localhost:8001
ORCHESTRATOR=http://localhost:8002
PHOENIX=http://localhost:6006
UI=http://localhost:3000

say() { printf "\n\033[1;36m▶ %s\033[0m\n" "$1"; }

wait_for() {
  local name=$1 url=$2 tries=${3:-60}
  printf "Waiting for %s" "$name"
  for _ in $(seq 1 "$tries"); do
    if curl -fsS "$url" >/dev/null 2>&1; then printf " ready\n"; return 0; fi
    printf "."; sleep 2
  done
  printf "\n%s never became ready at %s\n" "$name" "$url"; exit 1
}

say "Bringing up the stack"
make setup >/dev/null
docker compose up --build -d

wait_for "Governance API" "$GOVERNANCE/health"
wait_for "Eval Orchestrator" "$ORCHESTRATOR/health"
wait_for "Mock Gateway" "$GATEWAY/health"
wait_for "Phoenix" "$PHOENIX/healthz" 90

say "Seeding demo data"
docker compose run --rm seed python seed_data.py

say "Sending a live LLM call through the gateway"
CHAT=$(curl -fsS "$GATEWAY/v1/chat" -H 'content-type: application/json' -d '{
  "messages": [{"role":"user","content":"A customer asks for a refund after 25 days. How should I respond?"}],
  "operation_name": "chat",
  "temperature": 0.2,
  "agent": {"agent_id":"customer-support-refund","framework":"langgraph",
            "criticality":"critical","data_classification":"restricted",
            "business_unit":"retail-banking"}
}')
echo "$CHAT" | python3 -m json.tool

TRACE_ID=$(echo "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["trace_id"])')
SPAN_ID=$(echo "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["span_id"])')
OUTPUT=$(echo "$CHAT" | python3 -c 'import sys,json;print(json.load(sys.stdin)["content"])')

say "Running refund_policy_compliance on that live trace"
curl -fsS "$ORCHESTRATOR/run-eval" -H 'content-type: application/json' -d "$(python3 - "$TRACE_ID" "$SPAN_ID" "$OUTPUT" <<'PY'
import json, sys
trace_id, span_id, output = sys.argv[1], sys.argv[2], sys.argv[3]
print(json.dumps({
    "eval_id": "refund_policy_compliance",
    "traces": [{
        "trace_id": trace_id, "span_id": span_id,
        "input": "A customer asks for a refund after 25 days. How should I respond?",
        "output": output,
    }],
}))
PY
)" | python3 -m json.tool

cat <<EOF

✅ Demo complete.

  Experience UI       $UI            (Phase E)
  Phoenix             $PHOENIX
  Governance API docs $GOVERNANCE/docs
  Orchestrator docs   $ORCHESTRATOR/docs
  Gateway docs        $GATEWAY/docs

Inspect emitted eval events:
  grep gen_ai.evaluation.result otel-collector/output/otel-audit.jsonl | tail -1 | python3 -m json.tool
EOF

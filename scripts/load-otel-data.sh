#!/usr/bin/env bash
# Send a batch of sample LLM calls through the gateway to populate Phoenix with
# live traces (useful for exploring the Trace Explorer without the full demo).
set -euo pipefail
cd "$(dirname "$0")/.."

GATEWAY=${GATEWAY_URL:-http://localhost:8080}
COUNT=${1:-15}

prompts=(
  "What is your refund policy?"
  "Can I get a refund after 25 days?"
  "Summarize the latest claim status."
  "Review this function for bugs."
  "Write a tagline for our spring campaign."
)
agents=(
  "customer-support-refund langgraph critical restricted retail-banking"
  "internal-knowledge-assistant custom medium internal operations"
  "code-review-agent crewai low internal engineering"
  "vendor-claims-agent vendor high confidential insurance"
  "marketing-copy-generator custom low public marketing"
)

echo "Sending $COUNT calls to $GATEWAY ..."
for i in $(seq 1 "$COUNT"); do
  p=${prompts[$((RANDOM % ${#prompts[@]}))]}
  read -r aid fw crit dc bu <<<"${agents[$((RANDOM % ${#agents[@]}))]}"
  curl -fsS "$GATEWAY/v1/chat" -H 'content-type: application/json' -d "{
    \"messages\":[{\"role\":\"user\",\"content\":\"$p\"}],
    \"agent\":{\"agent_id\":\"$aid\",\"framework\":\"$fw\",\"criticality\":\"$crit\",
               \"data_classification\":\"$dc\",\"business_unit\":\"$bu\"}
  }" >/dev/null && printf "."
done
printf "\nDone. Open Phoenix at http://localhost:6006\n"

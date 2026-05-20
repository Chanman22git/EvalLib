#!/usr/bin/env bash
# Tear down the stack and wipe all state (volumes + collector output).
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose down -v
rm -f otel-collector/output/*.jsonl 2>/dev/null || true
echo "EvalLib reset: containers down, volumes removed, collector output cleared."

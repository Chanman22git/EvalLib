# OTel Collector

The single ingestion and processing point for all EvalLib telemetry.

## What it does

```
mock-gateway ─┐
              ├─ OTLP (gRPC :4317 / HTTP :4318) ─► Collector ─► Phoenix (traces)
eval-orchestr ┘                                            ├─► file (/output/otel-audit.jsonl)
                                                            ├─► debug (console)
                                                            └─► [Datadog / Splunk — optional]
```

| Stage | Component | Purpose |
|---|---|---|
| Receive | `otlp` | OTLP gRPC (4317) + HTTP (4318) from gateway & orchestrator |
| Process | `transform/pii_redaction` | Regex masking of emails, phones, SSNs, credit-card patterns in attribute values |
| Process | `resource/enrich` | Stamps `deployment.environment` + `service.namespace` |
| Process | `batch` | Batches before export (1s / 256 spans) |
| Export | `otlp/phoenix` | Traces → Phoenix (the trace backend) |
| Export | `file/audit` | Append-only `otel-audit.jsonl` for inspection & audit replay (AC-8) |
| Export | `debug` | Console output while developing |

Datadog and Splunk exporters are present but commented out — the POC emits OTel
and leaves downstream backends as-is (PRD NG1).

## Run

Started automatically by the root `docker-compose.yml`. Config lives in
[`otel-collector-config.yaml`](otel-collector-config.yaml). The file exporter
writes to a mounted `./otel-collector/output/` directory on the host.

## Inspecting eval events (AC-8)

```bash
grep gen_ai.evaluation.result otel-collector/output/otel-audit.jsonl | tail -1 | jq .
```

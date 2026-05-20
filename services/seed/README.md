# Seed & Demo

Populates the Governance Store with realistic POC data and provides the
end-to-end demo.

## What gets seeded (FR-SD-1)

- **5 agents** across criticalities/frameworks (refund [critical/langgraph],
  knowledge assistant, code review, third-party vendor, marketing).
- **8 evals** in a realistic mix of governance states (3 approved with
  calibration, plus in_review and draft), defined in
  [`sample_evals/evals.yaml`](sample_evals/evals.yaml).
- **3 calibration sets** in
  [`sample_evals/calibration_sets.yaml`](sample_evals/calibration_sets.yaml).
- **~290 eval results** spread over the past 7 days (covers the "200+ traces /
  50+ results" target — each result carries a distinct trace_id).
- **Change events**: benign weekly texture + the fake **"policy KB re-index"**.
- **1 injected regression**: `refund_policy_compliance` on the refund agent drops
  ~15% from day 5, just after the KB re-index — plus a seeded regression alert
  whose top candidate cause is that re-index (AC-7 groundwork; Phase F also
  detects it live).

> Live Phoenix traces are produced by the demo's gateway calls, not by the seed
> (OpenTelemetry can't backdate spans). The seed's historical data lives in the
> Governance Store mirror, which powers the dashboards and time-series.

## Run

```bash
make seed     # docker compose run --rm seed python seed_data.py
make demo     # full end-to-end: up → seed → live call → eval → URLs
```

Run `make reset` first if the store already has data — the seeder assumes a
fresh database.

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    governance_api_url: str = "http://governance-api:8001"
    gateway_url: str = "http://mock-gateway:8080"
    phoenix_base_url: str = "http://phoenix:6006"
    phoenix_project: str = "default"

    judge_default_model: str = "claude-sonnet-4-6"

    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "eval-orchestrator"
    deployment_environment: str = "poc"
    service_namespace: str = "evallib"

    # Sampled-online background worker.
    sampling_enabled: bool = True
    sampling_interval_seconds: float = 30.0

    # Regression detection job (FR-RD-1..3).
    regression_enabled: bool = True
    regression_interval_seconds: float = 900.0  # 15 minutes (PRD)
    # Window defaults are POC-tuned for the seed data's per-day cadence: the
    # "current" window is the most recent day and the baseline is the older
    # healthy span (days 2–7 ago), so a sustained drop is detectable.
    regression_current_window_hours: float = 24.0
    regression_baseline_lookback_days: float = 7.0
    regression_baseline_recent_cutoff_days: float = 2.0
    regression_min_samples: int = 3

    # Consolidated suite verdict: PASS only if mean score >= this threshold AND
    # no blocking eval failed (the verdict's `passed` is true).
    suite_pass_threshold: float = 0.75


settings = Settings()

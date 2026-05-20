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


settings = Settings()

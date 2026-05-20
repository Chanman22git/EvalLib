from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Mock gateway configuration, sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_mode: str = "mock"  # "mock" | "anthropic"
    anthropic_api_key: str = ""
    anthropic_base_url: str = "https://api.anthropic.com"
    gateway_default_model: str = "claude-sonnet-4-6"

    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "mock-gateway"
    deployment_environment: str = "poc"
    service_namespace: str = "evallib"
    otel_instrumentation_genai_capture_message_content: bool = True

    governance_api_url: str = "http://governance-api:8001"


settings = Settings()

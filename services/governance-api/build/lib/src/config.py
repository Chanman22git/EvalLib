from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://evallib:evallib_dev_pw@postgres:5432/evallib"

    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    otel_service_name: str = "governance-api"
    deployment_environment: str = "poc"
    service_namespace: str = "evallib"

    # Auto-create tables on startup (POC convenience; Alembic is the source of
    # truth for real migrations). Disabled under pytest, which uses create_all.
    auto_create_tables: bool = True


settings = Settings()

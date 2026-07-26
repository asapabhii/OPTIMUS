"""Application configuration — loaded from environment variables via Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configuration is environment-driven. No config files, no magic."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_env: Literal["development", "test", "staging", "production"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_log_level: str = "INFO"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # --- Primary Store: Neon (managed Postgres 16) ---
    database_url: str = Field(description="Async connection string (asyncpg)")
    database_url_sync: str = Field(default="", description="Sync connection string (for Alembic)")

    # --- Nango Cloud ---
    nango_secret_key: SecretStr = Field(description="Nango API secret key")
    nango_public_key: str = Field(default="", description="Nango public key for frontend")
    nango_base_url: str = "https://api.nango.dev"

    # --- Portkey (LLM Gateway) ---
    portkey_api_key: SecretStr = Field(description="Portkey API key")
    portkey_base_url: str = "https://api.portkey.ai/v1"

    # --- OpenAI (routed through Portkey) ---
    openai_api_key: SecretStr = Field(description="OpenAI API key")

    # --- Senzing ---
    senzing_license_key: str = Field(default="", description="Senzing evaluation license")

    # --- Grafana Cloud (OTel) ---
    grafana_otlp_endpoint: str = Field(
        default="", description="Grafana Cloud OTLP endpoint"
    )
    grafana_otlp_token: SecretStr = Field(
        default=SecretStr(""), description="Grafana Cloud OTLP auth token"
    )
    otel_service_name: str = "optimus-trustlayer"

    # --- Airbyte Cloud ---
    airbyte_api_key: str = Field(default="", description="Airbyte Cloud API key")
    airbyte_workspace_id: str = Field(default="", description="Airbyte workspace ID")

    # --- LlamaCloud ---
    llama_cloud_api_key: str = Field(default="", description="LlamaCloud API key")

    # --- Qdrant Cloud ---
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant endpoint")
    qdrant_api_key: str = Field(default="", description="Qdrant API key")

    # --- Redpanda Cloud ---
    redpanda_brokers: str = Field(default="localhost:9092", description="Redpanda bootstrap servers")
    redpanda_sasl_username: str = Field(default="")
    redpanda_sasl_password: SecretStr = Field(default=SecretStr(""))
    redpanda_security_protocol: str = "PLAINTEXT"
    redpanda_sasl_mechanism: str = "SCRAM-SHA-256"

    # --- Temporal Cloud ---
    temporal_namespace: str = Field(default="default", description="Temporal namespace")
    temporal_api_key: str = Field(default="")
    temporal_endpoint: str = Field(default="localhost:7233")

    # --- Google OAuth (for Nango-managed connectors) ---
    google_client_id: str = Field(default="")
    google_client_secret: SecretStr = Field(default=SecretStr(""))

    # --- Onboarding: fast-path ingestion ---
    fast_path_default_n: int = Field(
        default=50,
        description="Default number of most-recent items per source for fast-path onboarding",
    )
    backfill_max_depth_days: int = Field(
        default=365, description="Maximum backfill depth in days"
    )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]

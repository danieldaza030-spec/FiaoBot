"""Application configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application configuration values."""

    app_name: str = "fiadobot"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fiadobot"


def load_config() -> AppConfig:
    """Load the application configuration from environment variables."""

    return AppConfig(
        app_name=os.getenv("FIADOBOT_APP_NAME", "fiadobot"),
        environment=os.getenv("FIADOBOT_ENV", "development"),
        log_level=os.getenv("FIADOBOT_LOG_LEVEL", "INFO"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/fiadobot",
        ),
    )

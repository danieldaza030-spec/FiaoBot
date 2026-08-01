"""Application configuration helpers."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application configuration values.

    Args:
        app_name: Human-readable application name.
        environment: Deployment environment name.
        log_level: Desired application log level.
        database_url: SQLAlchemy connection string for PostgreSQL.
        llm_provider: Name of the configured LLM provider adapter.
        openai_api_key: API key used to authenticate with OpenAI.
        openai_model: Model identifier used for OpenAI chat completions.
        telegram_bot_token: Token used to authenticate with the Telegram Bot API.
        telegram_webhook_secret: Optional secret validated on inbound webhooks.
    """

    app_name: str = "fiadobot"
    environment: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fiadobot"
    llm_provider: str = "openai"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    telegram_bot_token: str | None = None
    telegram_webhook_secret: str | None = None


def load_config() -> AppConfig:
    """Load the application configuration from environment variables.

    Returns:
        The immutable configuration object built from environment variables.
    """

    return AppConfig(
        app_name=os.getenv("FIADOBOT_APP_NAME", "fiadobot"),
        environment=os.getenv("FIADOBOT_ENV", "development"),
        log_level=os.getenv("FIADOBOT_LOG_LEVEL", "INFO"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://postgres:postgres@localhost:5432/fiadobot",
        ),
        llm_provider=os.getenv("LLM_PROVIDER", "openai"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
        telegram_webhook_secret=os.getenv("TELEGRAM_WEBHOOK_SECRET"),
    )

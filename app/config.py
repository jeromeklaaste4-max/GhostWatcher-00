"""Application configuration.

All configuration values are loaded from environment variables (and the
local ``.env`` file, if present) using ``pydantic-settings``. A single
cached ``Settings`` instance is exposed via :func:`get_settings` so the
rest of the application can depend on it without re-parsing the
environment on every call.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly typed application settings.

    Values are read from environment variables. See ``.env.example`` for
    a full list of supported variables and their defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Telegram -----------------------------------------------------
    telegram_bot_token: str = Field(
        default="",
        description="Telegram bot token issued by @BotFather.",
    )
    telegram_chat_id: str = Field(
        default="",
        description="Telegram chat/channel/group ID to deliver alerts to.",
    )
    telegram_api_base_url: str = Field(
        default="https://api.telegram.org",
        description="Base URL for the Telegram Bot API (overridable for testing).",
    )

    # --- Webhook security -----------------------------------------------
    webhook_secret: str = Field(
        default="change-me",
        description="Secret path segment TradingView must include in the webhook URL.",
    )

    # --- Database -------------------------------------------------------
    database_url: str = Field(
        default="sqlite:///./ghostwatcher.db",
        description="SQLAlchemy database URL.",
    )

    # --- Server -----------------------------------------------------------
    host: str = Field(default="0.0.0.0", description="Host interface to bind to.")
    port: int = Field(default=8000, description="Port to bind to.")

    # --- Alert behaviour --------------------------------------------------
    cooldown_seconds: int = Field(
        default=300,
        ge=0,
        description="Minimum number of seconds between duplicate alerts for the "
        "same symbol/timeframe/signal combination.",
    )
    wick_tolerance_percent: float = Field(
        default=0.0,
        ge=0.0,
        le=50.0,
        description="Allowed wick size as a percentage of the candle's total "
        "range before a candle is no longer considered 'wickless'.",
    )

    # --- Logging ------------------------------------------------------
    log_level: str = Field(default="INFO", description="Python logging level.")

    # --- HTTP client --------------------------------------------------
    http_timeout_seconds: float = Field(
        default=10.0, description="Timeout for outbound HTTP requests (Telegram)."
    )
    telegram_max_retries: int = Field(
        default=3, ge=0, description="Max retry attempts for Telegram delivery."
    )
    telegram_retry_backoff_seconds: float = Field(
        default=1.0, ge=0.0, description="Base backoff (seconds) between retries."
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Ensure the configured log level is a recognized Python logging level."""
        normalized = value.upper()
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if normalized not in valid_levels:
            raise ValueError(
                f"Invalid log level '{value}'. Must be one of {sorted(valid_levels)}."
            )
        return normalized

    @field_validator("webhook_secret")
    @classmethod
    def validate_webhook_secret(cls, value: str) -> str:
        """Warn-worthy but non-fatal: reject empty secrets outright."""
        if not value or not value.strip():
            raise ValueError("webhook_secret must not be empty.")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return a cached, process-wide :class:`Settings` instance."""
    return Settings()


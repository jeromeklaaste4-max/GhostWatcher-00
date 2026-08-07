"""Async Telegram Bot API client used to deliver trading signals."""

from __future__ import annotations

import logging

import httpx

from app.config import Settings, get_settings
from app.utils.retry import async_retry

logger = logging.getLogger(__name__)


class TelegramDeliveryError(RuntimeError):
    """Raised when a message could not be delivered to Telegram."""


class TelegramService:
    """Thin async wrapper around the Telegram Bot API ``sendMessage`` call."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    @property
    def is_configured(self) -> bool:
        """Whether both a bot token and chat ID have been provided."""
        return bool(self._settings.telegram_bot_token and self._settings.telegram_chat_id)

    def _send_url(self) -> str:
        return (
            f"{self._settings.telegram_api_base_url}"
            f"/bot{self._settings.telegram_bot_token}/sendMessage"
        )

    async def send_message(self, text: str, *, parse_mode: str = "Markdown") -> dict:
        """Send ``text`` to the configured Telegram chat.

        Retries transient failures (network errors, 5xx responses) with
        exponential backoff, configured via ``TELEGRAM_MAX_RETRIES`` and
        ``TELEGRAM_RETRY_BACKOFF_SECONDS``.

        Raises:
            TelegramDeliveryError: If the bot is not configured, or if
                delivery ultimately fails after all retry attempts.
        """
        if not self.is_configured:
            raise TelegramDeliveryError(
                "Telegram is not configured: set TELEGRAM_BOT_TOKEN and "
                "TELEGRAM_CHAT_ID in your environment."
            )

        retrying_send = async_retry(
            max_attempts=self._settings.telegram_max_retries,
            base_delay_seconds=self._settings.telegram_retry_backoff_seconds,
            exceptions=(httpx.HTTPError, TelegramDeliveryError),
        )(self._send_once)

        return await retrying_send(text, parse_mode)

    async def _send_once(self, text: str, parse_mode: str) -> dict:
        """Perform a single Telegram API call (no retry logic here)."""
        payload = {
            "chat_id": self._settings.telegram_chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }
        timeout = self._settings.http_timeout_seconds

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(self._send_url(), json=payload)

        if response.status_code >= 500:
            raise TelegramDeliveryError(
                f"Telegram server error: HTTP {response.status_code}"
            )

        data = response.json()

        if response.status_code >= 400 or not data.get("ok", False):
            description = data.get("description", "unknown error")
            raise TelegramDeliveryError(
                f"Telegram rejected the message: HTTP {response.status_code} - {description}"
            )

        logger.info("Telegram message delivered successfully.")
        return data


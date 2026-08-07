"""Orchestrates the full alert pipeline: detect, dedupe, store, notify."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.engine.wickless import Candle, WicklessDetector, WicklessSignal
from app.models.alert import Alert, AlertStatus, SignalType
from app.repository.alert_repository import AlertRepository
from app.schemas.webhook import TradingViewAlertPayload
from app.services.telegram import TelegramDeliveryError, TelegramService
from app.utils.formatter import format_alert_message

logger = logging.getLogger(__name__)

_SIGNAL_MAP = {
    WicklessSignal.BULLISH: SignalType.BULLISH_WICKLESS,
    WicklessSignal.BEARISH: SignalType.BEARISH_WICKLESS,
}


@dataclass(frozen=True, slots=True)
class AlertOutcome:
    """Result of processing a single webhook payload."""

    status: str
    message: str
    alert_id: int | None = None
    signal: str | None = None


class AlertService:
    """Coordinates candle detection, persistence, and Telegram delivery."""

    def __init__(
        self,
        session: Session,
        settings: Settings | None = None,
        telegram_service: TelegramService | None = None,
        detector: WicklessDetector | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._repository = AlertRepository(session)
        self._telegram = telegram_service or TelegramService(self._settings)
        self._detector = detector or WicklessDetector(
            tolerance_percent=self._settings.wick_tolerance_percent
        )

    async def process_alert(self, payload: TradingViewAlertPayload) -> AlertOutcome:
        """Run a TradingView payload through the full detection pipeline."""
        candle = Candle(
            open=payload.open, high=payload.high, low=payload.low, close=payload.close
        )

        detected = self._detector.detect(candle)

        if detected == WicklessSignal.NONE:
            logger.info(
                "No wickless pattern for %s (%s): O=%s H=%s L=%s C=%s",
                payload.symbol,
                payload.timeframe,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
            )
            return AlertOutcome(
                status="no_signal",
                message="No wickless candle pattern detected.",
            )

        signal_type = _SIGNAL_MAP[detected]

        duplicate = self._repository.find_recent_duplicate(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            signal=signal_type,
            cooldown_seconds=self._settings.cooldown_seconds,
        )
        if duplicate is not None:
            logger.info(
                "Duplicate alert suppressed for %s (%s) %s within cooldown window.",
                payload.symbol,
                payload.timeframe,
                signal_type.value,
            )
            return AlertOutcome(
                status="duplicate",
                message="A matching alert was already sent within the cooldown window.",
                alert_id=duplicate.id,
                signal=signal_type.value,
            )

        alert = self._repository.create_alert(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            signal=signal_type,
            price=payload.close,
            open_=candle.open,
            high=candle.high,
            low=candle.low,
            close=candle.close,
            status=AlertStatus.RECEIVED,
            candle_time=payload.time,
        )

        text = format_alert_message(
            symbol=payload.symbol,
            timeframe=payload.timeframe,
            signal=detected,
            candle=candle,
            candle_time=payload.time,
        )

        return await self._deliver(alert, text, signal_type)

    async def _deliver(
        self, alert: Alert, text: str, signal_type: SignalType
    ) -> AlertOutcome:
        """Attempt Telegram delivery and update the alert's stored status."""
        try:
            await self._telegram.send_message(text)
        except TelegramDeliveryError as exc:
            logger.error("Failed to deliver alert %s to Telegram: %s", alert.id, exc)
            self._repository.update_status(alert, AlertStatus.FAILED)
            return AlertOutcome(
                status="error",
                message=f"Signal detected but Telegram delivery failed: {exc}",
                alert_id=alert.id,
                signal=signal_type.value,
            )

        self._repository.update_status(alert, AlertStatus.SENT)
        return AlertOutcome(
            status="signal_sent",
            message="Signal detected and delivered to Telegram.",
            alert_id=alert.id,
            signal=signal_type.value,
        )


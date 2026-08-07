"""ORM model representing a stored trading alert."""

from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.repository.database import Base


class SignalType(str, enum.Enum):
    """Type of wickless signal detected on a candle."""

    BULLISH_WICKLESS = "BULLISH_WICKLESS"
    BEARISH_WICKLESS = "BEARISH_WICKLESS"


class AlertStatus(str, enum.Enum):
    """Lifecycle status of a stored alert."""

    RECEIVED = "RECEIVED"
    SENT = "SENT"
    DUPLICATE = "DUPLICATE"
    FAILED = "FAILED"


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (used as a column default)."""
    return datetime.now(timezone.utc)


class Alert(Base):
    """A single trading alert received from TradingView."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    signal: Mapped[str] = mapped_column(
        Enum(SignalType, native_enum=False, length=32), nullable=False, index=True
    )

    price: Mapped[float] = mapped_column(Float, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[str] = mapped_column(
        Enum(AlertStatus, native_enum=False, length=16),
        nullable=False,
        default=AlertStatus.RECEIVED.value,
    )

    candle_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper only
        return (
            f"Alert(id={self.id!r}, symbol={self.symbol!r}, "
            f"timeframe={self.timeframe!r}, signal={self.signal!r}, "
            f"status={self.status!r})"
        )


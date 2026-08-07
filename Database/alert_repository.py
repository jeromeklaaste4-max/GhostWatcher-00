"""Data access functions for the :class:`~app.models.alert.Alert` model."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertStatus, SignalType


class AlertRepository:
    """Encapsulates all SQL operations for trading alerts.

    A repository is constructed per-request with an injected SQLAlchemy
    :class:`~sqlalchemy.orm.Session`, keeping database access isolated from
    business logic in the service layer.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_alert(
        self,
        *,
        symbol: str,
        timeframe: str,
        signal: SignalType,
        price: float,
        open_: float,
        high: float,
        low: float,
        close: float,
        status: AlertStatus = AlertStatus.RECEIVED,
        candle_time: datetime | None = None,
    ) -> Alert:
        """Persist a new alert row and return the created instance."""
        alert = Alert(
            symbol=symbol,
            timeframe=timeframe,
            signal=signal.value,
            price=price,
            open=open_,
            high=high,
            low=low,
            close=close,
            status=status.value,
            candle_time=candle_time,
        )
        self._session.add(alert)
        self._session.commit()
        self._session.refresh(alert)
        return alert

    def update_status(self, alert: Alert, status: AlertStatus) -> Alert:
        """Update an alert's status and persist the change."""
        alert.status = status.value
        self._session.commit()
        self._session.refresh(alert)
        return alert

    def find_recent_duplicate(
        self,
        *,
        symbol: str,
        timeframe: str,
        signal: SignalType,
        cooldown_seconds: int,
        reference_time: datetime | None = None,
    ) -> Alert | None:
        """Return the most recent matching alert within the cooldown window.

        Two alerts are considered duplicates when they share the same
        symbol, timeframe, and signal type, and the earlier one was
        received less than ``cooldown_seconds`` before ``reference_time``.
        """
        if cooldown_seconds <= 0:
            return None

        now = reference_time or datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=cooldown_seconds)

        stmt = (
            select(Alert)
            .where(
                Alert.symbol == symbol,
                Alert.timeframe == timeframe,
                Alert.signal == signal.value,
                Alert.created_at >= window_start,
            )
            .order_by(Alert.created_at.desc())
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, alert_id: int) -> Alert | None:
        """Fetch a single alert by its primary key."""
        return self._session.get(Alert, alert_id)

    def list_recent(self, limit: int = 50) -> list[Alert]:
        """Return the most recently received alerts, newest first."""
        stmt = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
        return list(self._session.execute(stmt).scalars().all())

    def count_all(self) -> int:
        """Return the total number of stored alerts."""
        stmt = select(Alert)
        return len(list(self._session.execute(stmt).scalars().all()))


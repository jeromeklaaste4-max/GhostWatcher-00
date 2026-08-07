"""Pydantic schemas for exposing stored alerts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRead(BaseModel):
    """Serialized representation of a stored :class:`~app.models.alert.Alert`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    timeframe: str
    signal: str
    price: float
    open: float
    high: float
    low: float
    close: float
    status: str
    candle_time: datetime | None
    created_at: datetime


class HealthResponse(BaseModel):
    """Response body for the health check endpoint."""

    status: str
    version: str
    database: str
    telegram_configured: bool


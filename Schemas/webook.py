"""Pydantic schemas for the TradingView webhook endpoint."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TradingViewAlertPayload(BaseModel):
    """The JSON body TradingView sends when an alert fires.

    TradingView alert messages are fully customizable, so this schema
    only requires the fields GhostWatcher actually needs: the instrument,
    timeframe, and OHLC candle values. Configure your TradingView alert
    message to send a JSON payload matching this shape, for example::

        {
          "symbol": "{{ticker}}",
          "timeframe": "{{interval}}",
          "open": {{open}},
          "high": {{high}},
          "low": {{low}},
          "close": {{close}},
          "time": "{{timenow}}"
        }
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    symbol: str = Field(..., min_length=1, max_length=32, description="Ticker symbol, e.g. BTCUSDT.")
    timeframe: str = Field(..., min_length=1, max_length=16, description="Chart timeframe, e.g. 15, 1h, 1D.")
    open: float = Field(..., description="Candle open price.")
    high: float = Field(..., description="Candle high price.")
    low: float = Field(..., description="Candle low price.")
    close: float = Field(..., description="Candle close price.")
    time: datetime | None = Field(
        default=None, description="ISO-8601 timestamp of the candle, if provided."
    )

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, value: str) -> str:
        return value.upper()

    @field_validator("high")
    @classmethod
    def high_must_be_highest(cls, value: float, info) -> float:  # noqa: ANN001
        low = info.data.get("low")
        open_ = info.data.get("open")
        if low is not None and value < low:
            raise ValueError("high must be greater than or equal to low")
        return value

    @field_validator("low")
    @classmethod
    def low_non_negative(cls, value: float) -> float:
        if value < 0:
            raise ValueError("low must be non-negative")
        return value


class WebhookResponse(BaseModel):
    """Response returned to TradingView (or any webhook caller)."""

    status: str = Field(..., description="One of: signal_sent, no_signal, duplicate, error.")
    message: str = Field(..., description="Human-readable summary of what happened.")
    alert_id: int | None = Field(default=None, description="Database ID of the stored alert, if any.")
    signal: str | None = Field(default=None, description="Detected signal type, if any.")


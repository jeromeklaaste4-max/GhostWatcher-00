"""Formats detected signals into human-readable Telegram messages."""

from __future__ import annotations

from datetime import datetime

from app.engine.wickless import Candle, WicklessSignal

_SIGNAL_EMOJI = {
    WicklessSignal.BULLISH: "🟢",
    WicklessSignal.BEARISH: "🔴",
}

_SIGNAL_LABEL = {
    WicklessSignal.BULLISH: "BULLISH WICKLESS",
    WicklessSignal.BEARISH: "BEARISH WICKLESS",
}


def format_alert_message(
    *,
    symbol: str,
    timeframe: str,
    signal: WicklessSignal,
    candle: Candle,
    candle_time: datetime | None = None,
) -> str:
    """Build the Telegram message body for a detected signal.

    Args:
        symbol: Ticker symbol, e.g. ``"BTCUSDT"``.
        timeframe: Chart timeframe, e.g. ``"15"`` or ``"1h"``.
        signal: The detected :class:`WicklessSignal`.
        candle: The OHLC candle that triggered the signal.
        candle_time: Optional timestamp of the candle.

    Returns:
        A Markdown-formatted message ready to send via the Telegram Bot API.
    """
    if signal == WicklessSignal.NONE:
        raise ValueError("Cannot format a message for WicklessSignal.NONE")

    emoji = _SIGNAL_EMOJI[signal]
    label = _SIGNAL_LABEL[signal]

    lines = [
        f"{emoji} *{label}*",
        "",
        f"*Symbol:* `{symbol}`",
        f"*Timeframe:* `{timeframe}`",
        f"*Price:* `{candle.close}`",
        "",
        "*OHLC*",
        f"O: `{candle.open}`  H: `{candle.high}`",
        f"L: `{candle.low}`  C: `{candle.close}`",
    ]

    if candle_time is not None:
        lines.append("")
        lines.append(f"*Candle time:* `{candle_time.isoformat()}`")

    lines.append("")
    lines.append("_GhostWatcher_")

    return "\n".join(lines)


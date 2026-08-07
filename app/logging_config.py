
"""Structured logging configuration for GhostWatcher."""

from __future__ import annotations

import logging
import sys


class RequestContextFormatter(logging.Formatter):
    """Log formatter that produces compact, single-line, structured output."""

    default_fmt = (
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    def __init__(self) -> None:
        super().__init__(fmt=self.default_fmt, datefmt="%Y-%m-%dT%H:%M:%S%z")


def setup_logging(log_level: str = "INFO") -> None:
    """Configure root logging handlers for the whole application.

    This is idempotent: calling it multiple times will not duplicate
    handlers, which matters for test suites that import the app repeatedly.

    Args:
        log_level: The desired root log level, e.g. ``"INFO"``.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Avoid attaching duplicate handlers on repeated setup calls.
    if any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.setLevel(log_level.upper())
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(RequestContextFormatter())
    root_logger.addHandler(handler)

    # Quiet down noisy third-party loggers unless we're in DEBUG mode.
    if log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger."""
    return logging.getLogger(name)

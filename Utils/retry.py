"""A minimal async retry helper with exponential backoff.

Kept dependency-free (no ``tenacity``) to minimize the project's
footprint, in keeping with GhostWatcher's "zero recurring cost, minimal
dependencies" philosophy.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


def async_retry(
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator that retries an async function with exponential backoff.

    Args:
        max_attempts: Total number of attempts before giving up (>= 1).
        base_delay_seconds: Base delay used for exponential backoff
            (``delay = base_delay_seconds * 2 ** attempt_index``).
        exceptions: Tuple of exception types that should trigger a retry.
            Any other exception propagates immediately.

    Returns:
        A decorator that wraps an async callable with retry behavior.
    """
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: object, **kwargs: object) -> T:
            last_exception: BaseException | None = None
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # noqa: BLE001 - intentional broad catch
                    last_exception = exc
                    is_last_attempt = attempt == max_attempts - 1
                    if is_last_attempt:
                        logger.error(
                            "%s failed after %d attempt(s): %s",
                            func.__name__,
                            max_attempts,
                            exc,
                        )
                        raise
                    delay = base_delay_seconds * (2**attempt)
                    logger.warning(
                        "%s failed (attempt %d/%d): %s. Retrying in %.1fs...",
                        func.__name__,
                        attempt + 1,
                        max_attempts,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
            # Unreachable in practice, but keeps type checkers happy.
            if last_exception is not None:  # pragma: no cover
                raise last_exception
            raise RuntimeError("async_retry exited without result or exception")  # pragma: no cover

        return wrapper

    return decorator


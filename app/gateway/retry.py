import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

from app.config import get_settings

T = TypeVar("T")


async def with_retry(
    func: Callable[[], Awaitable[T]],
    *,
    max_attempts: int | None = None,
    base_delay: float | None = None,
) -> T:
    settings = get_settings()
    attempts = max_attempts or settings.retry_max_attempts
    delay = base_delay or settings.retry_base_delay
    last_error: Exception | None = None

    for attempt in range(attempts):
        try:
            return await func()
        except Exception as exc:
            last_error = exc
            if attempt < attempts - 1:
                await asyncio.sleep(delay * (2**attempt))
    assert last_error is not None
    raise last_error

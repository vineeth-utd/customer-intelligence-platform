"""Reusable reference-resolution retry helper for cross-topic eventual consistency."""

import asyncio
from typing import Awaitable, Callable, TypeVar

from app.config.settings import settings

T = TypeVar("T")


async def resolve_reference(
    lookup_fn: Callable[[], Awaitable[T | None]],
    *,
    timeout: float | None = None,
    interval: float | None = None,
    max_attempts: int | None = None,
    predicate: Callable[[T], bool] | None = None,
) -> T | None:
    """Resolve an asynchronous reference with bounded polling and configuration-driven retry.

    Calls lookup_fn(). If the result is None (or fails the optional predicate), sleeps for `interval`
    and retries until `timeout` or `max_attempts` has elapsed.
    """
    total_timeout = timeout if timeout is not None else settings.reference_resolution_timeout_seconds
    sleep_interval = interval if interval is not None else settings.reference_resolution_interval_seconds
    max_tries = max_attempts if max_attempts is not None else max(1, int(total_timeout / sleep_interval) + 1)

    loop = asyncio.get_running_loop()
    deadline = loop.time() + total_timeout

    attempt = 0
    while True:
        attempt += 1
        res = await lookup_fn()
        if res is not None:
            if predicate is None or predicate(res):
                return res

        if attempt >= max_tries:
            break

        remaining = deadline - loop.time()
        if remaining <= 0:
            break

        await asyncio.sleep(min(sleep_interval, remaining))

    return None

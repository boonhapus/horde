"""
Public utility functions for working with horde.
"""
from __future__ import annotations
from typing import Any, Callable
import functools as ft
import asyncio

import horde._compat


def async_memoize(async_fn: Callable) -> Callable:
    """
    Remember the result of <async_fn>.
    """
    if not horde._compat.iscoroutinefunction(async_fn):
        raise RuntimeError(f"a coroutine function is required, got {async_fn}")

    _cache = {}

    def _chain_task_to_future(f: asyncio.Future, t: asyncio.Task) -> Any:
        # PRIORITY ORDER:
        # 1. Cancel the future.
        if t.cancelled():
            f.cancel()
            return

        # 2. Set any raised Exceptions.
        t_exc = t.exception()

        if t_exc is not None:
            f.set_exception(t_exc)
            return

        # 3. Set the result.
        f.set_result(t.result())

    @ft.wraps(async_fn)
    async def _decorated(*a, **kw) -> Any:
        # Make the key from the function name + args + kwargs.
        k: list[str] = ft._make_key((async_fn.__name__, *a), kw, typed=False)
        f: asyncio.Future = _cache.get(k)

        # See if our work is ready to process.
        if f is not None:
            if not f.done():
                # continue waiting on it to be done
                # shield: don't cancel what the user doesn't know about.
                return await asyncio.shield(f)

            return f.result()  # which may raise Exception

        # Create a user-facing awaitable.
        loop = asyncio.get_event_loop()
        f = loop.create_future()

        # Schedule the work.
        t = loop.create_task(async_fn(*a, **kw))

        # Chain the awaitables together.
        t.add_done_callback(ft.partial(_chain_task_to_future, f))

        # Cache our user-facing awaitable.
        _cache[k] = f

        # wait on it to be done
        # shield: don't cancel what the user doesn't know about.
        return await asyncio.shield(f)

    return _decorated

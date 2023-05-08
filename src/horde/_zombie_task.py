from __future__ import annotations
from typing import Any, Callable
import functools as ft
import warnings
import asyncio


class ZombieTask:
    """
    Work for a Zombie to do.
    """

    __slots__ = ("fn", "weight", "_loop")

    def __init__(self, fn: Callable, weight: int = 1):
        self.fn = fn
        self.weight = weight
        self._loop: asyncio.BaseEventLoop = None

    @property
    def __name__(self) -> str:
        return self.fn.__qualname__

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        if self._loop is None:
            self._loop = asyncio.get_running_loop()

        return self._loop

    def copy(self, fn: Callable = None, weight: int = None) -> ZombieTask:
        """
        Create a new copy of this task.
        """
        keywords = {
            "fn": self.fn if fn is None else fn,
            "weight": self.weight if weight is None else weight,
        }
        return ZombieTask(**keywords)

    def __call__(self, *a, **kw) -> Any:
        if asyncio.iscoroutinefunction(self.fn):
            coro = self.fn(*a, **kw)
        else:
            func = ft.partial(self.fn, *a, **kw)
            coro = self.loop.run_in_executor(None, func)

        return coro


#
#
#


def task(fn: Callable = None, *, weight: int = 1):
    """
    Mark this function as a Zombie task.
    """
    if fn is None:
        return ft.partial(task, weight=weight)

    if hasattr(fn, "__zombie_task__"):
        warnings.warn(f"{fn.__qualname__} is already a task! redefining with weight={weight}")

    fn.__zombie_task__ = ZombieTask(fn=fn, weight=weight)
    return fn

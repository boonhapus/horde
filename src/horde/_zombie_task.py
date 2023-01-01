from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
import functools as ft
import warnings

from horde._compat import IS_PY_310_COMPATIBLE


@dataclass(slots=IS_PY_310_COMPATIBLE)
class ZombieTask:
    """
    Work for a Zombie to do.
    """
    fn: Callable
    weight: int = 1

    def copy(self, fn: Callable) -> ZombieTask:
        """
        Create a new copy of this task, optionally with a new function.
        """
        return ZombieTask(fn=fn, weight=self.weight)

    def __call__(self, *a, **kw) -> Any:
        return self.fn(*a, **kw)


#
#
#

def task(fn: Callable=None, *, weight: int=1):
    """
    Mark this function as a Zombie task.
    """
    if fn is None:
        return ft.partial(task, weight=weight)

    if hasattr(fn, "__zombie_task__"):
        warnings.warn(f"{fn.__qualname__} is already a task! redefining with {weight=}")

    fn.__zombie_task__ = ZombieTask(fn=fn, weight=weight)
    return fn

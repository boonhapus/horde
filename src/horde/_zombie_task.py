from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable
from typing import TYPE_CHECKING
import functools as ft
import warnings
import asyncio
import random

from horde._state import ZombieState
from horde.errors import StopZombie
import horde.events


if TYPE_CHECKING:
    from horde.environment import Environment
    from horde._zombie import Zombie


@dataclass
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


class TaskSet:
    """
    All the work a Zombie can perform.
    """
    def __init__(self, zombie: Zombie):
        self._zombie = zombie
        self._tasks = []

    @property
    def environment(self) -> Environment:
        return self._zombie.environment

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        return self._zombie.environment._loop

    def append(self, task: ZombieTask) -> None:
        """
        Add a task to the set.
        """
        self._tasks.append(task)

    def _raise_if_stopped(self) -> None:
        if self._zombie._state == ZombieState.stopping:
            raise StopZombie()

    def _wait_time(self) -> float:
        if not hasattr(self._zombie, "task_delay"):
            return 0.0
        return self._zombie.__class__.task_delay()

    async def run(self):
        while True:

            if self._tasks:
                zombie_task, *_ = random.choices(self._tasks, [t.weight for t in self._tasks], k=1)
                self._raise_if_stopped()
                self.environment.events.fire(horde.events.EVT_ZOMBIE_TASK_BEGIN)
                await zombie_task()
                self._raise_if_stopped()
                self.environment.events.fire(horde.events.EVT_ZOMBIE_TASK_END)

            await self.wait()

    async def wait(self):
        self._raise_if_stopped()
        self._zombie._state = ZombieState.waiting
        await asyncio.sleep(self._wait_time())
        self._raise_if_stopped()
        self._zombie._state = ZombieState.running


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

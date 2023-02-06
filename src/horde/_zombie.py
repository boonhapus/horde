from __future__ import annotations
from typing import TYPE_CHECKING
import functools as ft
import datetime as dt
import asyncio
import inspect
import logging
import random

from horde._state import ZombieState
from horde.errors import StopZombie
from horde import delay
import horde._compat
import horde.events

if TYPE_CHECKING:
    from horde.environment import Environment

log = logging.getLogger(__name__)


class Zombie:
    """ """

    stop_on_error: bool = False
    task_delay: delay.WaitCalculator = delay.seconds(0.0)

    def __init__(self, environment: Environment, zombie_id: int):
        self.environment = environment
        self.zombie_id = zombie_id
        self._state = ZombieState.inactive
        self._tasks = []
        self._process_zombie_for_tasks()

    @property
    def horde(self):
        return self.environment

    @property
    def name(self) -> str:
        return getattr(self, "_name", self.__class__.__name__)

    @property
    def state(self) -> ZombieState:
        return self._state

    @state.setter
    def state(self, new_state: ZombieState) -> None:
        if new_state not in (ZombieState.stopping, ZombieState.stopped):
            self._check_if_stopping()

        self._state = new_state

    def _process_zombie_for_tasks(self) -> None:
        is_zombie_task = ft.partial(lambda member: hasattr(member, "__zombie_task__"))

        for name, member in inspect.getmembers(self, predicate=is_zombie_task):
            # DEV NOTE: @boonhapus, 2022/12/28
            # OK, this feels like a dirty hack... maybe we should actually figure out
            # how descriptors work. we're decorating a function on a class with info
            # about the type work (task) that should be done, which also needs to bound
            # to the instance.
            #
            # That SOUNDS like a descriptor to me, but I'm not able to figure out how to
            # make it work. :(
            #
            zombie_task = member.__zombie_task__.copy(fn=member)
            self._tasks.append(zombie_task)

    def _check_if_stopping(self) -> None:
        if self._state == ZombieState.stopping or self.environment.runner.is_despawning:
            raise StopZombie()

    async def _run(self) -> None:

        self.state = ZombieState.starting
        await self.on_start()
        self.state = ZombieState.running

        while self._tasks:
            # gather stats
            zombie_task, *_ = random.choices(self._tasks, [t.weight for t in self._tasks], k=1)
            now = dt.datetime.now()
            start: float = horde._compat.get_time()

            try:
                self._check_if_stopping()
                self.environment.events.fire(
                    horde.events.ZombieTaskBegin(source=self, zombie=self, zombie_task=zombie_task, start_time=now)
                )

                r = await zombie_task()
                self._check_if_stopping()

                self.environment.events.fire(
                    horde.events.ZombieTaskFinish(
                        source=self,
                        zombie=self,
                        zombie_task=zombie_task,
                        start_time=now,
                        elapsed=dt.timedelta(seconds=horde._compat.get_time() - start),
                        result=r,
                    )
                )

                await self.wait()

            except (StopZombie, asyncio.CancelledError):
                break

            except Exception as e:
                self.environment.events.fire(
                    horde.events.ErrorInZombieTask(
                        source=self,
                        zombie=self,
                        zombie_task=zombie_task,
                        start_time=now,
                        elapsed=dt.timedelta(seconds=horde._compat.get_time() - start),
                        exception=e,
                    )
                )

                if self.stop_on_error:
                    break

        self.state = ZombieState.stopping
        await self.on_stop()
        self.state = ZombieState.stopped

    async def on_start(self) -> None:
        """
        Called when a Zombie starts running.
        """
        pass

    async def on_stop(self) -> None:
        """
        Called when a Zombie stops running.
        """
        pass

    async def wait(self) -> None:
        self.state = ZombieState.waiting
        await asyncio.sleep(self.task_delay())
        self.state = ZombieState.running

    def stop(self, force: bool = False) -> None:
        self.state = ZombieState.stopping

        if force:
            # reach into the event loop queue and cancel the Zombie & its tasks.
            raise NotImplementedError("not yet..")

    def __repr__(self):
        return f"{self.__class__.__name__}(zombie_id={self.zombie_id}, state={self._state.value})"

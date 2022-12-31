from __future__ import annotations
import functools as ft
import asyncio
import inspect

from horde._zombie_task import ZombieTasks
from horde._state import ZombieState
from horde.errors import StopZombie
import horde.events


class Zombie:
    """
    """

    def __init__(self, environment, zombie_id: int):
        self.environment = environment
        self.zombie_id = zombie_id
        self._state = ZombieState.inactive
        self._tasks = ZombieTasks(self)
        self._process_zombie_for_tasks()

    def _process_zombie_for_tasks(self) -> None:
        is_zombie_task = ft.partial(lambda member: hasattr(member, "__zombie_task__"))

        for name, member in inspect.getmembers(self._zombie, predicate=is_zombie_task):
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

    async def on_start(self) -> None:
        """
        Called when a User starts running.
        """
        pass

    async def on_stop(self) -> None:
        """
        Called when a User stops running.
        """
        pass

    async def run(self, max_zombies_semaphore: asyncio.Semaphore) -> None:
        self._state = ZombieState.running

        try:
            await self.on_start()
            await self._tasks.run()

        except Exception as e:
            if not isinstance(e, (StopZombie, asyncio.CancelledError)):
                self.environment.events.fire(horde.events.EVT_ERROR_IN_ZOMBIE, zombie=self, exception=e)

        finally:
            self._state = ZombieState.stopping
            await self.on_stop()
            max_zombies_semaphore.release()
            self._state = ZombieState.stopped

    def stop(self, force: bool=False) -> None:
        self._state = ZombieState.stopping

        if force:
            # reach into the environment and cancel the User task and the taskset task.
            raise NotImplementedError("not yet..")

    def __repr__(self):
        return f"{self.__class__.__name__}(zombie_id={self.zombie_id}, state={self._state.value})"

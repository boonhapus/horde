from __future__ import annotations
import functools as ft
import asyncio
import inspect
import logging
import random

from horde._state import ZombieState
from horde.errors import StopZombie
from horde import delay
import horde.events

log = logging.getLogger(__name__)


class Zombie:
    """
    """
    stop_on_error: bool = False
    task_delay: delay.WaitCalculator = delay.seconds(0.0)

    def __init__(self, environment, zombie_id: int):
        self.environment = environment
        self.zombie_id = zombie_id
        self._state = ZombieState.inactive
        self._tasks = []
        self._process_zombie_for_tasks()

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

    async def _run(self, max_zombies_semaphore: asyncio.Semaphore) -> None:

        try:
            self._check_if_stopping()
            self._state = ZombieState.starting
            await self.on_start()
            self._check_if_stopping()
            self._state = ZombieState.running

            while self._tasks:
                try:
                    self._check_if_stopping()
                    zombie_task, *_ = random.choices(self._tasks, [t.weight for t in self._tasks], k=1)
                    self.environment.events.fire(horde.events.EVT_ZOMBIE_TASK_BEGIN)
                    await zombie_task()
                    self._check_if_stopping()
                    self.environment.events.fire(horde.events.EVT_ZOMBIE_TASK_END)
                    await self.wait()

                except (StopZombie, asyncio.CancelledError):
                    break

                except Exception as e:
                    self.environment.events.fire(horde.events.EVT_ERROR_IN_ZOMBIE, zombie=self, exception=e)

                    if self.stop_on_error:
                        break

        except (StopZombie, asyncio.CancelledError):
            pass

        except Exception:
            log.error(f"error in {self.__class__.__name__}.on_start (#{self.zombie_id}); see logs for details..")
            log.debug("", exc_info=True)

        finally:
            if self._state != ZombieState.starting:
                try:
                    self._state = ZombieState.stopping
                    await self.on_stop()
                except Exception:
                    log.error(f"error in {self.__class__.__name__}.on_stop (#{self.zombie_id}); see logs for details..")
                    log.debug("", exc_info=True)

            max_zombies_semaphore.release()
            self._state = ZombieState.stopped

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
        self._check_if_stopping()
        self._state = ZombieState.waiting
        await asyncio.sleep(self.task_delay())
        self._check_if_stopping()
        self._state = ZombieState.running

    def stop(self, force: bool=False) -> None:
        self._state = ZombieState.stopping

        if force:
            # reach into the event loop queue and cancel the Zombie & its tasks.
            raise NotImplementedError("not yet..")

    def __repr__(self):
        return f"{self.__class__.__name__}(zombie_id={self.zombie_id}, state={self._state.value})"

from __future__ import annotations
from typing import TYPE_CHECKING
import functools as ft
import warnings
import asyncio

from horde.spawn_policy import RoundRobinSpawnPolicy
from horde._state import RunnerState
import horde.events

if TYPE_CHECKING:
    from horde.spawn_policy import SpawnPolicy


class Runner:
    """
    """

    def __init__(self, environment):
        self.environment = environment
        self.state = RunnerState.inactive
        self.max_concurrent_zombies: int = None
        self._background_zombie_spawner_task: asyncio.Task = None
        self._running_tasks = set()
        self._running_zombies = set()

    @property
    def is_inactive(self) -> bool:
        return self.state == RunnerState.inactive

    @property
    def is_running(self) -> bool:
        return self.state == RunnerState.running

    @property
    def is_spawning(self) -> bool:
        return self.state == RunnerState.spawning

    @property
    def is_stopping(self) -> bool:
        return self.state == RunnerState.stopping

    async def _spawner(self, policy: SpawnPolicy, rate: float) -> None:
        initial_spawn = 0
        initial_spawn_complete = False
        semaphore = asyncio.Semaphore(self.max_concurrent_zombies)

        for idx, zombie_cls in enumerate(policy, start=1):
            if not (self.is_spawning or self.is_running):
                break

            await semaphore.acquire()
            zombie = zombie_cls(self.environment, zombie_id=idx)
            t = self.environment._loop.create_task(zombie.run(semaphore))
            t.__horde_zombie__ = zombie
            self.environment.events.fire(horde.events.EVT_SPAWN_ZOMBIE)

            # add it to the internal tasks queue
            self._running_tasks.add(t)
            self._running_zombies.add(zombie)

            # remove it once the worker is done
            t.add_done_callback(lambda t: self._running_tasks.discard(t))
            t.add_done_callback(lambda t: self._running_zombies.discard(t.__horde_zombie__))

            if not initial_spawn_complete:
                initial_spawn += 1

                if initial_spawn >= self.max_concurrent_zombies:
                    initial_spawn_complete = True
                    self.environment.events.fire(horde.events.EVT_SPAWN_COMPLETE)
                    self.state = RunnerState.running

            await asyncio.sleep(1.0 / rate)

    async def start(
        self,
        *,
        number_of_zombies: int,
        spawn_rate: float = 1.0,
        spawn_policy_cls: SpawnPolicy = RoundRobinSpawnPolicy,
        total_execution_time: float = None,
    ):
        """

        Parameters
        ----------
        number_of_zombies : int
          total number of zombies to spawn

        spawn_rate : float = 1.0
          amount of zombies to spawn per second

        spawn_policy_cls : SpawnPolicy = RoundRobinSpawnPolicy
          how to spawn zombies, see horde.policy for more details

        total_execution_time : float = None
          number of seconds to run the spawner for

          This does not account for execution time of each User.
          The value 'None' represents "run forever".
        """
        f = self.environment.events.fire(horde.events.EVT_INIT)
        await asyncio.gather(*f)

        if not self.is_inactive:
            return

        self.max_concurrent_zombies = number_of_zombies
        self.state = RunnerState.spawning
        self.environment.events.fire(horde.events.EVT_SPAWN_START)

        spawn_policy = spawn_policy_cls(self.environment.zombie_classes)
        spawner_coro = self._spawner(policy=spawn_policy, rate=spawn_rate)
        self._background_zombie_spawner_task = self.environment._loop.create_task(spawner_coro)

        if total_execution_time is not None:
            call_stop = ft.partial(self.environment._loop.create_task, self.stop())
            self.environment._loop.call_later(max(0, total_execution_time), call_stop)

    async def join(self) -> None:
        try:
            await self._background_zombie_spawner_task
        except asyncio.CancelledError:
            pass

        # allow tasks on the stack to process
        await asyncio.sleep(0)

        try:
            await self._background_stop_task
        except asyncio.CancelledError:
            pass

    async def stop(self):
        self._background_stop_task = asyncio.current_task()

        if self.is_spawning:
            warnings.warn("Environment.runner.stop() called during initial spawn!", UserWarning)

        self._background_zombie_spawner_task.cancel()
        self.state = RunnerState.despawning
        self.environment.events.fire(horde.events.EVT_DESPAWN_START)

        for zombie in self._running_zombies:
            zombie.stop()

        if self._running_tasks:
            await asyncio.gather(*self._running_tasks)

        fs = self.environment.events.fire(horde.events.EVT_DESPAWN_COMPLETE)
        await asyncio.gather(*fs)

        self.state = RunnerState.inactive
        fs = self.environment.events.fire(horde.events.EVT_STOP)
        await asyncio.gather(*fs)

from __future__ import annotations
from typing import TYPE_CHECKING
import functools as ft
import warnings
import logging
import asyncio

from horde.spawn_policy import RoundRobinSpawnPolicy
from horde._state import RunnerState
from horde.errors import StopZombie
import horde.events

if TYPE_CHECKING:
    from horde.spawn_policy import SpawnPolicy

log = logging.getLogger(__name__)


class Runner:
    """
    """

    def __init__(self, environment):
        self.environment = environment
        self.state = RunnerState.inactive
        self.max_concurrent_zombies: int = None
        self._background_zombie_spawner_task: asyncio.Task = None
        self._running_zombies = {}
        self._horde_is_running_event = asyncio.Event()
        self._max_zombies_semaphore: asyncio.Semaphore = None

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
    def is_despawning(self) -> bool:
        return self.state == RunnerState.despawning

    @property
    def is_stopping(self) -> bool:
        return self.state == RunnerState.stopping

    @property
    def active_zombies(self) -> int:
        return len(self._running_zombies)

    def _handle_zombie_done(self, future: asyncio.Future) -> None:
        zombie = self._running_zombies.pop(future.__horde_zombie_id__)

        try:
            future.result()
        except (StopZombie, asyncio.CancelledError):
            pass
        except Exception as e:
            log.error(f"{e} in {zombie.__class__.__name__}.on_start (#{zombie.zombie_id}); see logs for details..")
            log.debug("", exc_info=True)
        finally:
            self._max_zombies_semaphore.release()

    async def _spawner(self, policy: SpawnPolicy, rate: float) -> None:
        total_zombies_spawned = 0
        initial_spawn_complete = False

        for iteration, (zombie_cls, n_zombies) in enumerate(policy, start=1):
            if not (self.is_spawning or self.is_running):
                break

            for _ in range(n_zombies):
                await self._max_zombies_semaphore.acquire()
                total_zombies_spawned += 1

                zombie = zombie_cls(self.environment, zombie_id=total_zombies_spawned)
                f = self.environment._loop.create_task(zombie._run())
                self.environment.events.fire(horde.events.SpawnZombie(source=self, zombie=zombie))

                # add it to the internal tasks queue
                self._running_zombies[zombie.zombie_id] = zombie
                f.__horde_zombie_id__ = zombie.zombie_id
                f.add_done_callback(self._handle_zombie_done)

                if not initial_spawn_complete and total_zombies_spawned >= self.max_concurrent_zombies:
                    initial_spawn_complete = True
                    self.environment.events.fire(horde.events.InitialSpawnComplete(source=self))
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
        # multiple calls have no effect
        if not self.is_inactive:
            return

        futures = self.environment.events.fire(horde.events.HordeInit(source=self))
        await asyncio.gather(*futures)

        self.max_concurrent_zombies = number_of_zombies
        self._max_zombies_semaphore = asyncio.Semaphore(number_of_zombies)

        self.state = RunnerState.spawning
        self.environment.events.fire(horde.events.InitialSpawnStart(source=self))

        spawn_policy = spawn_policy_cls(self.environment.zombie_classes)
        spawner_coro = self._spawner(policy=spawn_policy, rate=spawn_rate)
        self._background_zombie_spawner_task = self.environment._loop.create_task(spawner_coro)

        if total_execution_time is not None:
            call_stop = ft.partial(self.environment._loop.create_task, self.stop())
            self.environment._loop.call_later(max(0, total_execution_time), call_stop)

    async def join(self) -> None:
        return await self._horde_is_running_event.wait()

    async def stop(self):
        if self.is_spawning:
            warnings.warn("Environment.runner.stop() called during initial spawn!", UserWarning)

        self._background_zombie_spawner_task.cancel()
        self.state = RunnerState.despawning
        self.environment.events.fire(horde.events.DespawnStart(source=self))

        # stop the active zombies
        for zombie_id, zombie in self._running_zombies.items():
            zombie.stop()

        futures = self.environment.events.fire(horde.events.DespawnComplete(source=self))
        await asyncio.gather(*futures)

        self.state = RunnerState.stopping
        futures = self.environment.events.fire(horde.events.HordeStop(source=self))
        await asyncio.gather(*futures)

        # allow the futures spawned from HordeStop callbacks to process
        await asyncio.sleep(0)

        # unblock anything waiting on the horde to finish
        self._horde_is_running_event.set()

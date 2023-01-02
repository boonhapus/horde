from __future__ import annotations
from typing import TYPE_CHECKING
import datetime as dt
import typing

from horde._util import camel_to_snake
import horde._compat

if TYPE_CHECKING:
    import horde

_registered_event_types: list[Event] = []


class Event:
    """
    Base class for all Horde events.
    """

    __slots__ = (
        "source",
        "_created_at",
    )

    def __init__(self, source):
        self.source = source
        self._created_at: float = horde._compat.get_time()

    def __init_subclass__(cls):
        super().__init_subclass__()
        cls.name = camel_to_snake(cls.__name__)
        _registered_event_types.append(cls)

    @property
    def name(self) -> str:
        """
        The name of the event.
        """
        return self.__class__.name

    def __str__(self) -> str:
        return f"<HordeEvent: '{self.name}' (from {self.source.__name__})>"


class Any(Event):
    """
    Sent along with any of the below events.
    """

    __slots__ = ("fired_event",)

    def __init__(self, source: typing.Any, fired_event: Event):
        super().__init__(source)
        self.fired_event = fired_event


class HordeInit(Event):
    """
    Sent when the Horde begins.
    """


class InitialSpawnStart(Event):
    """
    Sent when the Horde runner beings to spawn Zombies.
    """


class SpawnZombie(Event):
    """
    Sent when the Horde runner spawns a Zombie.
    """

    __slots__ = ("zombie",)

    def __init__(self, source: Any, zombie: horde.Zombie):
        super().__init__(source)
        self.zombie = zombie


class InitialSpawnComplete(Event):
    """
    Sent when the Horde runner finishes the initial spawn.
    """


class DespawnStart(Event):
    """
    Sent when the Horde runner stops spawning Zombies.
    """


class DespawnComplete(Event):
    """
    Sent when no Zombies remain.
    """


class ZombieTaskBegin(Event):
    """
    Sent when a ZombieTask starts.
    """

    __slots__ = (
        "zombie",
        "zombie_task",
        "start_time",
    )

    def __init__(self, source: Any, zombie: horde.Zombie, zombie_task: horde.ZombieTask, start_time: dt.datetime):
        super().__init__(source)
        self.zombie = zombie
        self.zombie_task = zombie_task
        self.start_time = start_time


class ZombieTaskFinish(Event):
    """
    Sent when a ZombieTask ends.
    """

    __slots__ = (
        "zombie",
        "zombie_task",
        "start_time",
        "elapsed",
        "result",
    )

    def __init__(
        self,
        source: Any,
        zombie: horde.Zombie,
        zombie_task: horde.ZombieTask,
        start_time: dt.datetime,
        elapsed: dt.timedelta,
        result: Any,
    ):
        super().__init__(source)
        self.zombie = zombie
        self.zombie_task = zombie_task
        self.start_time = start_time
        self.elapsed = elapsed
        self.result = result


class ErrorInZombieTask(Event):
    """
    Sent when a ZombieTask ends.
    """

    __slots__ = (
        "zombie",
        "zombie_task",
        "start_time",
        "elapsed",
        "exception",
    )

    def __init__(
        self,
        source: Any,
        zombie: horde.Zombie,
        zombie_task: horde.ZombieTask,
        start_time: dt.datetime,
        elapsed: dt.timedelta,
        exception: Exception,
    ):
        super().__init__(source)
        self.zombie = zombie
        self.zombie_task = zombie_task
        self.start_time = start_time
        self.elapsed = elapsed
        self.exception = exception


class HTTPZombieRequestComplete(Event):
    """
    Sent when a HTTPZombie receives a server response.
    """

    __slots__ = (
        "zombie",
        "request",
        "response",
        "request_url",
        "request_start_time",
        "response_elapsed_time",
        "response_length",
        "exception",
    )

    def __init__(
        self,
        source: Any,
        request: Any,  # most likely httpx.Request
        response: Any,  # most likely httpx.Response
        request_url: str,
        request_start_time: dt.datetime,
        response_elapsed_time: dt.timedelta,
        response_length: int,
        exception: Exception,  # most likely httpx.HTTPStatusError
    ):
        super().__init__(source)
        self.zombie: horde.Zombie = source
        self.request = request
        self.response = response
        self.request_url = request_url
        self.request_start_time = request_start_time
        self.response_elapsed_time = response_elapsed_time
        self.response_length = response_length
        self.exception = exception


class HordeStop(Event):
    """
    Sent when the Horde is called off.
    """

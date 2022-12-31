from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
import warnings
import asyncio
import logging

import horde.events

log = logging.getLogger(__name__)


@dataclass(unsafe_hash=True)
class EventHook:
    event_name: str
    handlers: list[Callable] = None
    event_loop: asyncio.BaseEventLoop = None

    def __post_init__(self):
        self.handlers = [] if self.handlers is None else self.handlers

    def add_listener(self, handler: Callable) -> None:
        self.handlers.append(handler)

    def remove_listener(self, handler: Callable) -> None:
        self.handlers.remove(handler)

    def _fire(self, *a, **kw) -> list[asyncio.Future]:
        if not self.handlers:
            return []

        # do we need to a threading pid check and asyncio.run_coroutine_threadsafe ?
        return [self.event_loop.create_task(listener(*a, **kw)) for listener in self.handlers]


class EventBus:
    """
    """
    def __init__(self, loop):
        self._loop = loop
        self._events = {event_name: EventHook(event_name, event_loop=loop) for event_name in horde.events.__all__}

    def __getattr__(self, attr_name: str) -> EventHook | Any:
        if attr_name in self._events:
            return self._events[attr_name]

        raise AttributeError(f"EventBus has no registered event or attribute named '{attr_name}'")

    def register(self, event_name: str, *, listeners: list[Callable] = None) -> None:
        """
        Add a new EventHook into the bus.
        """
        event_name = event_name.lower()
        listeners = [] if listeners is None else listeners

        if event_name == "fire":
            raise ValueError("event_name can not be 'fire'!")

        if event_name in self._events:
            warnings.warn(f"overriding currently registered event with name '{event_name}'", UserWarning)

        self._events[event_name] = EventHook(event_name, handlers=listeners)

    def fire(self, event_name: str, *a, **kw) -> list[asyncio.Future]:
        event_name = event_name.lower()
        event = self._events.get(event_name, None)

        if event is None:
            warnings.warn(f"no event has been registered by name '{event_name}'", UserWarning)
            return

        self._events[horde.events.EVT_ANY]._fire(*a, event_name=event_name, **kw)
        return event._fire(*a, **kw)

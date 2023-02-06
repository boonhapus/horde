from __future__ import annotations
from collections.abc import Callable
from typing import Any, List
import warnings
import asyncio
import logging

from horde._async import invoke
from horde._util import camel_to_snake
import horde.events

log = logging.getLogger(__name__)


class EventHook:
    """
    A mechanism to tie Horde work to Events.
    """

    __slots__ = (
        "event_cls",
        "handlers",
    )

    def __init__(self, event: horde.events.Event, handlers: List[Callable] = None):
        self.event_cls = event
        self.handlers = [] if handlers is None else handlers

    def add_listener(self, handler: Callable) -> None:
        self.handlers.append(handler)

    def remove_listener(self, handler: Callable) -> None:
        self.handlers.remove(handler)

    def __repr__(self) -> None:
        return f"<EventHook '{self.event_cls.name}' with {len(self.handlers)} listeners>"


class EventBus:
    """
    A means of communication for the Horde.

    All actions in the horde trigger an event.
    """

    def __init__(self, loop):
        self._loop = loop
        self._hooks = {event.name: EventHook(event) for event in horde.events._registered_event_types}

    def __getattr__(self, attr_name: str) -> EventHook | Any:

        try:
            return self._hooks[camel_to_snake(attr_name)]
        except KeyError:
            pass

        raise AttributeError(f"EventBus has no registered event or attribute named '{attr_name}'")

    def register(self, event_cls: horde.events.Event, *, listeners: List[Callable] = None) -> None:
        """
        Add a new EventHook into the bus.
        """
        listeners = [] if listeners is None else listeners

        if event_cls.name == "fire":
            raise ValueError("event_name can not be 'fire'!")

        if event_cls.name in self._hooks:
            warnings.warn(f"overriding currently registered event with name '{event_cls.name}'", UserWarning)

        self._hooks[event_cls.name] = EventHook(event_cls, handlers=listeners)

    def add_listener(self, event: horde.events.Event, *, listener: Callable) -> None:
        """
        Add a handler to the Event.
        """
        self._hooks[event.name].add_listener(listener)

    def remove_listener(self, event: horde.events.Event, *, listener: Callable) -> None:
        """
        Remove a handler to the Event.
        """
        self._hooks[event.name].remove_listener(listener)

    def _fire(self, *, hook: horde.events.EventHook, event: horde.events.Event):
        futures: asyncio.Task = []

        for listener in hook.handlers:
            coro = invoke(listener, event)
            futures.append(self._loop.create_task(coro))

        return futures

    def fire(self, event: horde.events.Event) -> List[asyncio.Future]:
        """
        Fire an event on the bus.
        """
        event_hook = self._hooks.get(event.name, None)

        if event_hook is None:
            warnings.warn(f"no event has been registered by name '{event.name}'", UserWarning)
            return

        # Fire the "any" event.
        any_event_hook = self._hooks["any"]
        any_event = any_event_hook.event_cls(source=self, fired_event=event)
        self._fire(hook=any_event_hook, event=any_event)

        return self._fire(hook=event_hook, event=event)

from typing import Any


class StatsRecorder:

    def __init__(self, environment):
        self.environment = environment
        self._events = []

        environment.events.any.add_listener(self.record_it_all)

    async def record_it_all(self, **kw):
        self._events.append(kw)

    def _cast(self, item, type_):
        return type_(item)

    def filter(self, event_name: str, *, cast=None) -> list[dict[str, Any]]:
        if cast is not None:
            return [{k: self._cast(v, cast) for k, v in e.items()} for e in self._events if e["event_name"] == event_name]
        return [_ for _ in self._events if _["event_name"] == event_name]

    def all(self, *, cast=None) -> list[dict[str, Any]]:
        if cast is not None:
            return [{k: self._cast(v, cast) for k, v in e.items()} for e in self._events]
        return self._events

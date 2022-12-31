from typing import Any


class StatsRecorder:

    def __init__(self, environment):
        self.environment = environment
        self._events = []

        environment.events.any.add_listener(self.record_it_all)

    async def record_it_all(self, **kw):
        self._events.append(kw)

    def filter(self, event_name: str) -> list[dict[str, Any]]:
        return [_ for _ in self._events if _["event_name"] == event_name]

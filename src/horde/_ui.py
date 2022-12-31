import asyncio


class UI:

    def __init__(self, environment):
        self.environment = environment

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        return self.environment._loop

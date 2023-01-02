from __future__ import annotations
from typing import TYPE_CHECKING
import asyncio

if TYPE_CHECKING:
    from horde.environment import Environment


class UI:

    def __init__(self, environment):
        self.environment = environment

    @property
    def loop(self) -> asyncio.BaseEventLoop:
        return self.environment._loop
    
    @property
    def horde(self) -> Environment:
        return self.environment

from typing import Callable
import functools as ft
import itertools as it

from horde._zombie import Zombie


class SpawnPolicy:
    """
    Spawn policies represent an infinite iterator.
    """
    def __init__(self, zombie_classes: list[Zombie]):
        self.zombie_classes = zombie_classes

    def __iter__(self):
        return self

    def __next__(self) -> tuple[Zombie, int]:
        return self.shape()


class RoundRobinSpawnPolicy(SpawnPolicy):
    """
    """

    def __init__(self, zombie_classes: list[Zombie], *, sort_key: Callable = None):
        if sort_key is None:
            sort_key = ft.partial(lambda zombie_cls: zombie_cls.__name__)

        self.zombie_classes = zombie_classes
        self._actual_iterator = it.cycle(sorted(self.zombie_classes, key=sort_key))

    def shape(self) -> tuple[Zombie, int]:
        """
        """
        return next(self._actual_iterator), 1

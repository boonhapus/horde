from __future__ import annotations
from typing import NewType, Callable
from typing import TYPE_CHECKING
import random
import time

if TYPE_CHECKING:
    from horde import Zombie

WaitCalculator = NewType("WaitCalculator", Callable[[], float])


def between(min_wait: float, max_wait: float) -> WaitCalculator:
    """
    Wait for a random amount of time between two amounts.
    """
    def _determine_wait(zombie: Zombie) -> float:
        return random.uniform(min_wait, max_wait)

    return _determine_wait


def seconds(n_seconds: float) -> WaitCalculator:
    """
    Wait a constant amount of time.
    """
    def _determine_wait(zombie: Zombie) -> float:
        return n_seconds * 1.0

    return _determine_wait


def paced(n_seconds: float) -> WaitCalculator:
    """
    Wait a maximum of `n_seconds`, minus the last execution delta.

    If the amount of time since the last execution is greater than `n_seconds`, then the
    result of this will be a no-op, or 0s wait time.
    """
    last_called_at = time.perf_counter()

    def _determine_wait(zombie: Zombie) -> float:
        nonlocal last_called_at

        elapsed = time.perf_counter() - last_called_at
        to_wait = max(0, n_seconds - elapsed)
        last_called_at += elapsed
        return to_wait

    return _determine_wait


def throughput(n_tasks: int) -> WaitCalculator:
    """
    Wait a maximum of 1s, divided by the number of tasks to execute.

    If the amount of time since the last execution is greater than `n_seconds`, then the
    result of this will be a no-op, or 0s wait time.
    """
    if n_tasks < 1:
        raise ValueError(f"'n_tasks' cannot be less than 1, got {n_tasks=}")

    return paced(1 / n_tasks)

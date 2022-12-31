import enum


class RunnerState(enum.Enum):
    """
    Represents the state of a Runner.
    """
    inactive = "INACTIVE"
    spawning = "SPAWNING"
    running = "RUNNING"
    despawning = "DESPAWNING"
    stopping = "STOPPING"


class ZombieState(enum.Enum):
    """
    Represents the state of a User.
    """
    inactive = "INACTIVE"
    running = "RUNNING"
    waiting = "WAITING"
    stopping = "STOPPING"
    stopped = "STOPPED"

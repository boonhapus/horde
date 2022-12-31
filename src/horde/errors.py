
class HordeError(Exception):
    """
    All horde exceptions inherit from this one.
    """


class StopZombie(HordeError):
    """
    Called on stopping a Zombie.
    """
    pass

# DEFAULT EVENTS

__all__ = (
    "EVT_ANY",
    "EVT_INIT",
    "EVT_SPAWN_START",
    "EVT_SPAWN_ZOMBIE",
    "EVT_SPAWN_COMPLETE",
    "EVT_DESPAWN_START",
    "EVT_DESPAWN_COMPLETE",
    "EVT_ZOMBIE_TASK_BEGIN",
    "EVT_ZOMBIE_TASK_END",
    "EVT_ERROR_IN_ZOMBIE",
    "EVT_REQUEST_COMPLETE",
    "EVT_STOP",
)


# fmt: off

EVT_ANY = "any"
# Fired along with all of the below events. Inherits keywords from all of the below events.

EVT_INIT = "init"
# Fired once a Runner starts.

EVT_SPAWN_START = "initial_spawn_start"
# Fired when a Runner begins to spawn Zombies.

EVT_SPAWN_ZOMBIE = "spawn_zombie"
# Fired when a Runner spawns a Zombie.

EVT_SPAWN_COMPLETE = "initial_spawn_complete"
# Fired when a Runner completes spawning Zombies.

EVT_DESPAWN_START = "despawn_start"
# Fired when a Runner stops spawning Zombies, allowing them to despawn.

EVT_DESPAWN_COMPLETE = "despawn_complete"
# Fired when no more spawned Zombies remain.

EVT_ZOMBIE_TASK_BEGIN = "zombie_task_begin"
# Fired when a Zombie starts a task.

EVT_ZOMBIE_TASK_END = "zombie_task_end"
# Fired when a Zombie finishes a task.

EVT_ERROR_IN_ZOMBIE = "error_in_zombie"
# Fired when a Zombie encounters an error during a task.

EVT_REQUEST_COMPLETE = "request_complete"
# Fired when an HTTP-based Zombie complete a web request.

EVT_STOP = "stop"
# Fired once a Runner stops.

# fmt: on

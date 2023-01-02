import traceback
import logging
import pathlib
import enum

from typer import Typer, Context, Argument, Option, Exit

from horde.cli._logging import rich_console, setup_logging
from horde.environment import Environment
from horde.cli._async import typer_async_hack
from horde import Zombie
import horde.events

log = logging.getLogger(__name__)
app = Typer(
    name="horde",
    help=("Join the Horde! 🧟" "\n\n" "horde is a performance testing framework written on top of asyncio."),
    options_metavar="[--option, ..., --help]",
    add_completion=False,
    no_args_is_help=True,
    context_settings={
        "help_option_names": ["--help", "-h"],
        "show_default": False,
        "token_normalize_func": str.casefold,
    },
)


class UIType(enum.Enum):
    headless = "headless"
    # terminal = "terminal"
    # website = "website"  # coming soon ;~)


def _collect_zombies(zombie_fp: pathlib.Path) -> list[Zombie]:
    from importlib.util import spec_from_file_location, module_from_spec
    import inspect

    spec = spec_from_file_location(f"horde.zombies.provided.{zombie_fp.stem}", zombie_fp.as_posix())
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    zombies_classes = []
    is_user_defined = lambda m: inspect.isclass(m) and "provided" in m.__module__

    for name, defined_class in inspect.getmembers(module, predicate=is_user_defined):
        if issubclass(defined_class, Zombie):
            zombies_classes.append(defined_class)

    return zombies_classes


def _mute_our_rich_handler() -> None:
    rich_handler = next(h for h in logging.getLogger().handlers if hasattr(h, "console") and h.console == rich_console)
    rich_handler.setLevel(logging.CRITICAL)


def _handle_exception(event: horde.events.Event) -> None:
    print(
        f"Unhandled error in Zombie #{event.zombie.zombie_id} -> {event.zombie_task.__name__}()"
        f"\n{traceback.print_exception(type(event.exception), event.exception, event.exception.__traceback__)}"
    )


@app.command(help=app.info.help, context_settings=app.info.context_settings)
@typer_async_hack
async def main(
    ctx: Context,
    zombie: pathlib.Path = Argument(
        ...,
        help=".py script to import, containing Zombie testing strategies",
        show_default=False,
        dir_okay=False,
    ),
    ui_type: UIType = Option(
        "headless",
        "--user-interface",
        "-i",
        help="which type of interface to run",
        show_default=True,
    ),
    verbosity: int = Option(
        0,
        "--verbose",
        "-v",
        metavar="",
        help="verbosity level of logs, can be included multiple times",
        show_default=False,
        count=True,
    ),
    output_directory: pathlib.Path = Option(
        None,
        "--output-dir",
        "-d",
        help="folder to write logs and test reports to - if ommitted, don't save data",
        file_okay=False,
    ),
    url: str = Option(
        ...,
        "--url",
        help="hostname to load test against",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
    n_zombies: int = Option(
        ...,
        "--zombies",
        help="total number of zombies to spawn",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
    spawn_rate: int = Option(
        1,
        "--spawn-rate",
        help="how many zombies to spawn each second",
        show_default=True,
        rich_help_panel="Zombie Spawner Options",
    ),
    runtime_seconds: float = Option(
        None,
        "--runtime",
        help="seconds to run the test for - if omitted, run forever",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
):
    setup_logging(level_no=verbosity, data_directory=output_directory)

    # ====================================================[ SETUP ]====================================================

    env = Environment(url, zombie_classes=_collect_zombies(zombie))
    env.create_runner("local")
    env.create_stats_recorder()
    env.events.add_listener(horde.events.ErrorInZombieTask, listener=_handle_exception)

    # ===============================================[ USER INTERFACES ]===============================================

    runner_kw = {"number_of_zombies": n_zombies, "spawn_rate": spawn_rate, "total_execution_time": runtime_seconds}

    if ui_type == UIType.headless:
        env.create_ui("printer")
        exit_code = await env.ui.printer.start(console=rich_console, **runner_kw)

    # coming soon!
    #
    # if ui_type == UIType.terminal:
    #     # terminal UI will cover the existing rich.console, let's mute it
    #     _mute_our_rich_handler()

    #     env.create_ui(UIType.terminal.value)
    #     await env.ui.terminal.start(**runner_kw)

    # if ui_type == UIType.website:
    #     env.create_ui("website", output_directory=output_directory)
    #     await env.ui.website.start()

    # ===============================================[ STATS RECORDERS ]===============================================

    # for stats, recorder in env.stats.items():
    #     if recorder.should_save:
    #         recorder.dump(output_directory)

    #
    # Basic example
    #

    # now = dt.datetime.now()

    # if output_directory is not None:
    #     date_fmt = "%Y_%m_%dT%H-%M-%S"
    #     events = json.dumps(env.stats.memory.all(cast=str), indent=4)
    #     output_directory.joinpath(f"horde_run_{now:{date_fmt}}_all_events.json").write_text(events)

    #     events = json.dumps(env.stats.memory.filter(horde.events.EVT_REQUEST_COMPLETE, cast=str), indent=4)
    #     output_directory.joinpath(f"horde_run_{now:{date_fmt}}_http_requests.json").write_text(events)

    # stats = env.stats.memory.filter(horde.events.EVT_REQUEST_COMPLETE)
    # min_time = stats[0]['request_start_time']
    # max_time = stats[-1]['request_start_time'] + stats[-1]['response_elapsed_time']

    # errors = [str(_["error"]).split("\n")[0] for _ in stats if _['exception'] is not None]
    # errors_str = "\n\t- " + "\n\t- ".join(errors)

    # log.info(
    #     f"=== [PERFORMANCE RUN STATISTICS] ==="
    #     f"\n       requests made: {len(stats): >3}"
    #     f"\n      execution time: {(max_time - min_time).total_seconds(): >6.2f}s"
    #     f"\n     latency average: {statistics.fmean([_['response_elapsed_time'].total_seconds() for _ in stats]): >6.2f}s"
    #     f"\n          error rate: {len([_ for _ in stats if _['exception']]) / len(stats): >6.2f}%"
    #     f"\n              errors: {errors_str if errors else 'None'}"
    #     f"\n===================================="
    #     f"\n"
    # )

    raise Exit(code=exit_code)

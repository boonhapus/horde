import statistics
import datetime as dt
import logging
import pathlib
import enum
import json

from pynput import keyboard
from typer import Typer, Context, Argument, Option

from horde.cli._logging import rich_console, setup_logging
from horde.cli._async import typer_async_hack
from horde import Zombie
import horde.events

log = logging.getLogger(__name__)
app = Typer(
    name="horde",
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
    terminal = "terminal"
    website = "website"


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


async def _handle_exception(**kw):
    print(kw)


@app.command(options_metavar="[--option, ..., --help]", context_settings=app.info.context_settings)
@typer_async_hack
async def main(
    ctx: Context,
    zombie: pathlib.Path = Argument(
        ...,
        help=".py script to import, containing a Zombie test strategy",
        show_default=False,
        dir_okay=False,
    ),
    ui_type: UIType = Option(
        "headless", "--user-interface", "-i",
        help="which type of interface to run",
        show_default=True,
    ),
    verbosity: int = Option(
        0, "--verbose", "-v",
        metavar="",
        help="verbosity level of logs, can be included multiple times",
        show_default=False,
        count=True,
    ),
    output_directory: pathlib.Path = Option(
        None, "--output-dir", "-d",
        help="folder to write logs and test reports to - if ommitted, don't save data",
        file_okay=False,
    ),
    url: str = Option(
        ..., "--url",
        help="hostname to load test against",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
    n_zombies: int = Option(
        ..., "--zombies",
        help="total number of zombies to spawn",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
    spawn_rate: int = Option(
        1, "--spawn-rate",
        help="how many zombies to spawn each second",
        show_default=True,
        rich_help_panel="Zombie Spawner Options",
    ),
    runtime_seconds: float = Option(
        None, "--runtime",
        help="seconds to run the test for - if omitted, run forever",
        show_default=False,
        rich_help_panel="Zombie Spawner Options",
    ),
):
    now = dt.datetime.now()
    setup_logging(level_no=verbosity, data_directory=output_directory, include_console=ui_type == UIType.headless)

    env = horde.Environment(url, zombie_classes=_collect_zombies(zombie))
    env.create_runner("local")
    env.create_stats_recorder()
    env.events.add_listener(horde.events.EVT_ERROR_IN_ZOMBIE, listener=_handle_exception)

    if ui_type == UIType.headless:

        def _handle_quit():
            log.info("[b green]Q[/] was pressed! Stopping the Horde test..")
            env._loop.create_task(env.runner.stop())

        kb_listener = keyboard.GlobalHotKeys({"q": _handle_quit})
        kb_listener.start()

        env.create_ui("printer", print_fn=log.debug)

        with rich_console.status("no [b blue]runtime[/] was set, running forever.. press [b green]Q[/] to stop!"):
            kw = {"number_of_zombies": n_zombies, "spawn_rate": spawn_rate, "total_execution_time": runtime_seconds}
            await env.runner.start(**kw)
            await env.runner.join()

        kb_listener.stop()

        if output_directory is not None:
            date_fmt = "%Y_%m_%dT%H-%M-%S"
            events = json.dumps(env.stats.memory.all(cast=str), indent=4)
            output_directory.joinpath(f"horde_run_{now:{date_fmt}}_all_events.json").write_text(events)

            events = json.dumps(env.stats.memory.filter(horde.events.EVT_REQUEST_COMPLETE, cast=str), indent=4)
            output_directory.joinpath(f"horde_run_{now:{date_fmt}}_http_requests.json").write_text(events)

        stats = env.stats.memory.filter(horde.events.EVT_REQUEST_COMPLETE)
        min_time = stats[0]['request_start_time']
        max_time = stats[-1]['request_start_time'] + stats[-1]['response_elapsed_time']

        errors = [str(_["error"]).split("\n")[0] for _ in stats if _['exception'] is not None]
        errors_str = "\n\t- " + "\n\t- ".join(errors)

        log.info(
            f"=== [PERFORMANCE RUN STATISTICS] ==="
            f"\n       requests made: {len(stats): >3}"
            f"\n      execution time: {(max_time - min_time).total_seconds(): >6.2f}s"
            f"\n     latency average: {statistics.fmean([_['response_elapsed_time'].total_seconds() for _ in stats]): >6.2f}s"
            f"\n          error rate: {len([_ for _ in stats if _['exception']]) / len(stats): >6.2f}%"
            f"\n              errors: {errors_str if errors else 'None'}"
            f"\n===================================="
            f"\n"
        )

    elif ui_type == UIType.terminal:
        env.create_ui(UIType.terminal.value)

        kw = {"number_of_zombies": n_zombies, "spawn_rate": spawn_rate, "total_execution_time": runtime_seconds}
        await env.ui.terminal.start(**kw)

    else:
        env.create_ui("website", output_directory=output_directory)
        await env.ui.website.start()

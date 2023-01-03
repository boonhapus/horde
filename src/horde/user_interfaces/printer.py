from __future__ import annotations
from typing import Any
from statistics import mean
from collections.abc import Iterable
import itertools as it
import logging

from rich.console import Console
from rich.layout import Layout
from rich.align import Align
from rich.style import Style
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text
from pynput import keyboard
from rich import box
import httpx

from horde._ui import UI
from horde.events import SpawnZombie, HTTPZombieRequestComplete, DespawnStart, HordeStop
import horde

log = logging.getLogger(__name__)
HORDE_GREEN = Style(color="pale_green3")
NULL = Text("{null}", style="grey35")


def take(n: int, iterable: Iterable) -> list[Iterable]:
    """Return first n items of the iterable as a list."""
    return list(it.islice(iterable, n))


def rich_cast(value: Any) -> str:
    """Cast values for Rich."""
    return f"{value: .2f}" if isinstance(value, float) else str(value)


class ZombieRow:
    """
    Represent a row element in the UI Table.
    """

    __slots__ = (
        "_zombie",
        "_max_zombies",
        "data",
    )

    def __init__(self, zombie: "Zombie", *, max_zombies: int):
        self._zombie = zombie
        self._max_zombies = max_zombies
        self.data: list[HTTPZombieRequestComplete] = []

    def format_error(self, exception) -> str:
        if isinstance(exception, httpx.HTTPStatusError):
            error = "HTTP {0.status_code}: {0.request.url.path}".format(exception)
        else:
            error, *_ = str(exception).split("\n")

        return error

    def generate_row_data(self) -> list[str]:
        pad = len(str(self._max_zombies))
        requests = 0
        error = NULL
        errors = 0
        latencies = []

        for row in self.data:
            requests += 1
            latencies.append(row.response_elapsed_time.total_seconds())

            if row.exception is not None:
                errors += 1
                error, *_ = str(row.exception).split("\n")

        data = {
            "zombie_name": f":zombie: [green]#{self._zombie.zombie_id: >{pad}}[/]",
            "zombie_type": self._zombie.name,
            "last_request": self.data[-1].request_start_time.strftime("%H:%M:%S") if self.data else "Never",
            "last_error": error,
            "requests": requests,
            "errors": errors,
            "average_latency_s": mean(latencies) if latencies else NULL,
            "error_rate": errors / max(requests, 1) if requests else NULL,
        }

        return data


class PrinterUI(UI):
    """
    Simply prints output to the terminal.
    """

    def __init__(self, environment):
        super().__init__(environment)
        self.max_concurrent_zombies: int = None
        self.hotkeys = {
            "q": self._handle_quit,
            "+": self._handle_show_more_zombies,
            "-": self._handle_show_less_zombies,
        }
        self._data: dict[str, ZombieRow] = {}
        self._display: Live = None
        self._zombies_on_display = 25

    @property
    def horde_state(self) -> str:
        return self.horde.runner.state.value.upper()

    @property
    def _layout_caption(self) -> str:
        state_info = {
            "INACTIVE": {"color": "white", "tag": "the horde lies dormant.."},
            "SPAWNING": {"color": "cyan", "tag": "the horde is rising.."},
            "RUNNING": {"color": "green", "tag": "the horde attacks!"},
            "DESPAWNING": {"color": "orange", "tag": "calling off the horde.."},
            "STOPPING": {"color": "red", "tag": "the horde lies dormant.."},
        }
        c = state_info.get(self.horde_state, {}).get("color", "pale_green3")
        t = state_info.get(self.horde_state, {}).get("tag", "the horde is plotting..")

        return f"Horde state [bold {c}]{self.horde_state}[/] | {t}"

    @property
    def _layout_controls(self):
        if not hasattr(self, "_controls"):
            self._controls = Table.grid(padding=3)
            row_data = []

            for hotkey, handler in self.hotkeys.items():
                self._controls.add_column(justify="right")
                key = hotkey.upper()
                name = handler.__name__.replace("_handle_", "").title().replace("_", " ")
                row_data.append(f"[bold blue]{key}[/] {name}")

            self._controls.add_row(*row_data)

        return self._controls

    @property
    def _layout_header(self) -> Panel:
        header = Table.grid(expand=True)
        header.add_column(justify="left")
        header.add_column(justify="center", ratio=1)
        header.add_column(justify="right")
        header.add_row(
            f"runtime [b blue]{self.horde.runtime}[/]",
            ":zombie: Join the [b]Horde[/]!",
            self._layout_controls,
        )

        return Panel(header, style=HORDE_GREEN)

    def _handle_quit(self) -> None:
        self._table_caption = "Calling off the horde.."
        self.update()
        self.horde._loop.create_task(self.horde.runner.stop())

    def _handle_show_more_zombies(self) -> None:
        self._zombies_on_display += 1
        self.update()

    def _handle_show_less_zombies(self) -> None:
        self._zombies_on_display = max(5, self._zombies_on_display - 1)
        self.update()

    def _layout_add_zombie_row(self, event: horde.Event) -> None:
        self._data[event.zombie.zombie_id] = ZombieRow(event.zombie, max_zombies=self.max_concurrent_zombies)
        self.update()

    def _layout_update_zombie_row(self, event: horde.Event) -> None:
        self._data[event.zombie.zombie_id].data.append(event)
        self.update()

    def _layout_table(self) -> Table:
        table = Table(
            caption=self._layout_caption,
            box=box.SIMPLE_HEAD,
            show_footer=True,
            row_styles=["dim", ""],
            title_style=HORDE_GREEN,
            caption_style=HORDE_GREEN,
            width=150,
        )

        table.add_column("Zombie", justify="center")
        table.add_column("Type", justify="center", width=20)
        table.add_column("Last Request", justify="center")
        table.add_column("Last Error", justify="center", width=40, no_wrap=True)
        table.add_column("Requests", justify="right", footer_style=HORDE_GREEN)
        table.add_column("Errors", justify="right", footer_style=HORDE_GREEN)
        table.add_column("Avg Time (s)", justify="right", footer_style=HORDE_GREEN)
        table.add_column("Error (%)", justify="right", footer_style=HORDE_GREEN)

        total = {"requests": [], "errors": [], "average_latency_s": [], "error_rate": []}
        top_n = take(self._zombies_on_display, sorted(self._data.values(), key=lambda zr: len(zr.data), reverse=True))

        for zombie_row in top_n:
            data = zombie_row.generate_row_data()
            table.add_row(*map(rich_cast, data.values()))

            for name in total:
                if data[name] is NULL:
                    continue

                total[name].append(data[name])

        # add total row (footer)
        table.add_row(*["" * len(table.columns)])
        table.columns[4].footer = rich_cast(sum(total["requests"]))
        table.columns[5].footer = rich_cast(sum(total["errors"]))
        table.columns[6].footer = rich_cast(mean(total["average_latency_s"])) if total["average_latency_s"] else ""
        table.columns[7].footer = rich_cast(mean(total["error_rate"])) if total["error_rate"] else ""
        return table

    def _generate_layout(self) -> None:
        """
        Generate a Rich layout.
        """
        layout = Layout()

        layout.split(
            Layout(name="header", size=3),
            Layout(name="table"),
        )

        layout["header"].update(self._layout_header)
        layout["table"].update(Align.center(self._layout_table()))
        return layout

    def update(self, *, refresh: bool = False) -> None:
        """
        Update the table UI.
        """
        table = self._generate_layout()
        self._display.update(table, refresh=refresh)

    #
    #
    #

    async def start(self, *, clear_on_exit: bool = False, console: Console = Console(), **runner_kwargs) -> int:
        """
        Start the animation.
        """
        if console.size.width <= 150:
            log.warning("Terminal is not wide enough to properly fit the display, please maximize and run again")
            log.info(f" Current width: {console.size.width: >4}")
            log.info(f"Required width:  150")
            return 1

        self.max_concurrent_zombies = runner_kwargs["number_of_zombies"]
        kb_listener = keyboard.GlobalHotKeys(self.hotkeys)
        kb_listener.start()

        with Live(self._generate_layout(), console=console, refresh_per_second=20) as display:
            self._display = display

            self.horde.events.add_listener(SpawnZombie, listener=self._layout_add_zombie_row)
            self.horde.events.add_listener(HTTPZombieRequestComplete, listener=self._layout_update_zombie_row)
            self.horde.events.add_listener(DespawnStart, listener=lambda evt: self.update())
            self.horde.events.add_listener(HordeStop, listener=lambda evt: self.update())

            await self.horde.runner.start(**runner_kwargs)
            await self.horde.runner.join()

            # generate the final state of the table, so the on-screen is fully accurate
            self.update(refresh=True)

        kb_listener.stop()

        if clear_on_exit:
            console.clear()

        return 0

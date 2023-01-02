import asyncio

from textual.widgets._header import HeaderTitle, HeaderClock
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Static
from textual.widget import Widget
from textual.app import App, ComposeResult

from horde._ui import UI
import horde.events


class HordeHeader(Widget):
    """ """

    DEFAULT_CSS = """
    HordeHeader {
        dock: top;
        width: 100%;
        background: $foreground 5%;
        color: $text;
        height: 1;
    }  
    """

    def compose(self):
        yield HeaderTitle()
        yield HeaderClock()

    def on_mount(self) -> None:
        self.query_one(HeaderTitle).text = "Join the Horde!"


class HordeCounter(Static):

    count: reactive[str | int] = reactive(0, layout=True)

    def __init__(self, title, **textual_kw):
        super().__init__(**textual_kw)
        self._horde_title = title

    def render(self) -> str:
        return f"{self._horde_title} [b blue]{self.count}[/]"


class HordeLabel(Static):

    text: reactive[str] = reactive("", layout=True)

    def __init__(self, title, initial, **textual_kw):
        super().__init__(**textual_kw)
        self._horde_title = title
        self._initial = initial

    def render(self) -> str:
        return f"{self._horde_title} [b blue]{self._initial if not self.text else self.text}[/]"


class TUI(App):
    CSS = """
    Screen {
        layout: grid;
        grid-size: 3;
        grid-rows: 33% 66%;
    }

    .box {
        border: solid green;
        content-align: center middle;
        text-style: bold;
    }

    #data-table {
        column-span: 3;
        background: $primary;
        color: white;
    }
    """

    BINDINGS = [
        ("s", "horde_start", "Start the Horde"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, environment, *a, **kw):
        super().__init__(*a, **kw)

    def compose(self) -> ComposeResult:
        """Called to add widgets to the app."""
        yield HordeHeader()
        yield HordeLabel("Horde State", self.horde.runner.state.value, id="horde-state", classes="box")
        yield HordeCounter(":zombie: Zombie count", id="zombies", classes="box")
        yield HordeCounter(":globe_with_meridians: Requests made", id="requests", classes="box")
        # yield DataTable(id="data-table", classes="box")
        yield Footer()

    async def _update_horde_state(self, **kw) -> None:
        """Update the Zombie counter."""
        self.query_one("#horde-state").text = self.horde.runner.state.value

    async def _update_zombies(self, **kw) -> None:
        """Update the Zombie counter."""
        self.query_one("#zombies", HordeCounter).count = len(self.horde.runner._running_zombies)

    async def _update_requests(self, **kw) -> None:
        """Update the Request counter."""
        self.query_one("#requests", HordeCounter).count += 1

    # async def _update_data_table(
    #     self,
    #     zombie,
    #     request,
    #     response,
    #     request_url,
    #     request_start_time,
    #     response_elapsed_time,
    #     response_length,
    #     exception
    # ) -> None:
    #     """Update the Zombie counter."""
    #     table = self.query_one("#data-table")
    #     pad = len(str(self.horde.runner.max_concurrent_zombies))
    #     data = {
    #         "zombie": f"Zombie [b green]#{zombie.zombie_id: >{pad}}[/]",
    #         "request_start_time": request_start_time.strftime("%H:%M:%S"),
    #         "slug": request_url.path,
    #         "elapsed_time": response_elapsed_time.total_seconds(),
    #         "error": exception is None,
    #         "status_code": response.status_code
    #     }
    #     table.add_row(*list(map(str, data.values())))

    # def on_mount(self):
    #     table = self.query_one("#data-table")
    #     table.zebra_stripes = True
    #     table.show_cursor = False

    #     table.add_column("Zombie")
    #     table.add_column("Request Start Time")
    #     table.add_column("URL")
    #     table.add_column("Elapsed (ms)")
    #     table.add_column("Error?")
    #     table.add_column("Status Code")

    def action_horde_start(self) -> None:
        """Start the Horde."""
        if not self.horde.runner.is_inactive:
            return

        self.horde.events.add_listener(horde.events.SpawnZombie, listener=self._update_zombies)
        self.horde.events.add_listener(horde.events.HTTPZombieRequestComplete, listener=self._update_requests)
        # self.horde.events.add_listener(EVT_REQUEST_COMPLETE, listener=self._update_data_table)

        for event in (
            horde.events.HordeInit,
            horde.events.InitialSpawnStart,
            horde.events.InitialSpawnComplete,
            horde.events.DespawnStart,
            horde.events.DespawnComplete,
            horde.events.HordeStop,
        ):
            self.horde.events.add_listener(event, listener=self._update_horde_state)

        coro = self.horde.runner.start(**self._horde_runner_kwargs)
        asyncio.create_task(coro)

    async def action_quit(self) -> None:
        """Quit the app."""
        try:
            await self.horde.runner.stop()
        except AttributeError:
            pass

        self.exit()


class TerminalUI(UI):
    def __init__(self, environment):
        super().__init__(environment)
        self.tui = TUI(environment)

    async def start(self, **runner_kwargs):
        self.tui._horde_runner_kwargs = runner_kwargs
        await self.tui.run_async()

from __future__ import annotations
import asyncio

from horde.user_interfaces import PrinterUI
from horde.runners import LocalRunner
from horde import Zombie

from horde._recorder import StatsRecorder
from horde._runner import Runner
from horde._event import EventBus
from horde._util import ArbitraryState, AttributeDict
from horde._ui import UI


class Environment:

    def __init__(self, host: str, *, zombie_classes: list[Zombie]=None, loop: asyncio.BaseEventLoop=None):
        self.host = host
        self._loop = loop if loop is not None else asyncio.get_running_loop()
        self.zombie_classes = [] if zombie_classes is None else zombie_classes
        self.shared_state = ArbitraryState()
        self.events = EventBus(loop=self._loop)
        self.runner = None
        self.stats: AttributeDict[str, StatsRecorder] = AttributeDict()
        self.ui: AttributeDict[str, UI] = AttributeDict()

    def create_stats_recorder(self) -> None:
        self.stats["memory"] = stats = StatsRecorder(self)
        return stats

    def create_runner(self, runner_type: str | Runner, **passthru) -> Runner:
        interfaces = {
            "local": LocalRunner,
        }

        if isinstance(runner_type, str):
            try:
                runner_cls = interfaces[runner_type]
            except KeyError:
                raise ValueError(f"runner_type must be one of: {list(interfaces.keys())}") from None

        else:
            runner_cls = runner_type

        self.runner = runner_cls(self, **passthru)
        return self.runner

    def create_ui(self, ui_type: str | UI, *, ui_name: str = None, **passthru) -> UI:
        interfaces = {
            "printer": PrinterUI,
            # "terminal": TerminalUI,
            # "web": WebUI,
        }

        if isinstance(ui_type, str):
            try:
                ui_cls = interfaces[ui_type]
                ui_name = ui_type if ui_name is None else ui_name
            except KeyError:
                raise ValueError(f"ui_type must be one of: {list(interfaces.keys())}") from None

        else:
            ui_cls = ui_type
            ui_name = ui_type.__class__.__name__.lower() if ui_name is None else ui_name

        self.ui[ui_name] = ui = ui_cls(self, **passthru)
        return ui

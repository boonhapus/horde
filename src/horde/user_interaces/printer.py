from typing import Any, Callable

from horde._ui import UI


class PrinterUI(UI):
    """
    Simply prints output to the terminal.
    """
    def __init__(self, environment, print_fn: Callable[[Any], None]=print):
        super().__init__(environment)
        self.print_fn = print_fn

        # register listeners
        environment.events.any.add_listener(self._print)

    async def _print(self, event_name: str, **event_data):
        lines = [f"<< '{event_name}' received"]

        if event_data:
            lines.append(str(event_data))

        self.print_fn("\n".join(lines))

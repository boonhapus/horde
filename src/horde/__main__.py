import logging
import enum

import typer

log = logging.getLogger(__name__)
app = typer.Typer(name="horde")


class UIType(enum.Enum):
    headless = "headless"
    website = "website"


def _setup_logging() -> None:
    ...


@app.command()
def main(
    ctx: typer.Context,
    ui_type: UIType = typer.Option(UIType.headless, help=""),
    n_zombies: int = typer.Option(),
    ui_type: str = typer.Option(),
):
    ...


def cli() -> int:
    _setup_logging()

    try:
        app()
    except Exception as e:
        log.exception(f"unexpected error: {e}", exc_info=True)


if __name__ == "__main__":
    raise SystemExit(cli())

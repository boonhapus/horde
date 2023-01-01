import logging

from horde.cli import app


def main() -> int:
    """
    Entrypoint into horde.
    """
    log = logging.getLogger(__name__)

    try:
        app()
    except Exception as e:
        log.exception(f"unexpected error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

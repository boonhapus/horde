import datetime as dt
import logging.config
import logging
import pathlib

from rich.console import Console

rich_console = Console()


def _monkeypatch_logging_trace():
    # HTTPX defines the TRACE loglevel. (link: https://github.com/encode/httpx/blob/master/httpx/_utils.py#L232)
    #
    # We just need to monkeypatch it into the logging environment.
    def _trace_log_level(self, message, *args, **kwargs):
        if self.isEnabledFor(5):
            self._log(5, message, args, **kwargs)

    def _log_to_root(message, *args, **kwargs):
        logging.log(5, message, *args, **kwargs)

    setattr(logging.getLoggerClass(), "trace", _trace_log_level)
    setattr(logging, "trace", _log_to_root)


def setup_logging(*, level_no: int, data_directory: pathlib.Path = None) -> None:
    # 40 --> ERROR
    # 30 --> WARNING
    # 20 --> INFO
    # 10 --> DEBUG
    #  5 --> TRACE
    _monkeypatch_logging_trace()

    level_number = max(20 - (level_no * 10), 5)
    level = logging.getLevelName(level_number)

    if level_number >= 10:
        logging.getLogger("httpx").setLevel("INFO")

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "shell": {
                "format": "%(message)s",
            },
            "verbose": {
                "format": "[%(levelname)s - %(asctime)s] [%(name)s - %(module)s.%(funcName)s %(lineno)d] %(message)s"
            },
        },
        "handlers": {},
        "loggers": {},
        "root": {"level": "DEBUG", "handlers": []},
    }

    config["root"]["handlers"].append("to_console")
    config["handlers"]["to_console"] = {
        "formatter": "shell",
        "level": level,
        "class": "rich.logging.RichHandler",
        # rich.__init__ params...
        "console": rich_console,
        "show_level": True,
        "rich_tracebacks": True,
        "markup": True,
        "log_time_format": "[%X]",
    }

    if data_directory is not None:
        logs_dir = pathlib.Path(data_directory) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        now = dt.datetime.now().strftime("%Y-%m-%dT%H_%M_%S")

        config["root"]["handlers"].append("to_file")
        config["handlers"]["to_file"] = {
            "formatter": "verbose",
            "level": "DEBUG",  # user can override in their config file
            "class": "logging.FileHandler",
            "filename": f"{logs_dir}/{now}.log",
            "mode": "w",  # Create a new file for each run of cs_tools.
            "encoding": "utf-8",  # Handle unicode fun.
            "delay": True,  # Don't create a file if no logging is done.
        }

    logging.config.dictConfig(config)

"""Project logging helpers."""

import logging

from rich.logging import RichHandler


FORMAT = "%(message)s"
LOGGER_NAME = "dvc_dag"

logger = logging.getLogger(LOGGER_NAME)


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure the package logger for CLI output."""
    if not any(isinstance(handler, RichHandler) for handler in logger.handlers):
        handler = RichHandler(rich_tracebacks=True)
        handler.setFormatter(logging.Formatter(FORMAT, datefmt="[%X]"))
        logger.addHandler(handler)

    logger.setLevel(level)
    logger.propagate = False
    return logger

import logging

from rich.logging import RichHandler


FORMAT = "%(message)s"

logging.basicConfig(
    level="INFO",
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger("rich")
logger.setLevel(logging.INFO)

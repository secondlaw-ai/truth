import logging
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(show_path=False)],
)

log = logging.getLogger("rich")

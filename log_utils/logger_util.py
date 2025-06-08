import logging
import os
from logging.handlers import TimedRotatingFileHandler

from dotenv import load_dotenv

load_dotenv()

# Determine the environment
ENV = os.getenv("ENV", "production").lower()
LOG_TO_TERMINAL = os.getenv("LOG_TO_TERMINAL", "false").lower() == "true"

# Default log directory based on env
DEFAULT_LOG_DIR = (
    os.path.join(os.getcwd(), "logs")
    if ENV == "development"
    else os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "FixLife", "logs")
)

os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)


def get_logger(name: str, log_file: str = None, level=logging.INFO):
    """
    Create or get a logger.

    Args:
        name: Logger name.
        log_file: Optional log file name (ignored if log_to_terminal is True).
        level: Logging level.
        log_to_terminal: Force logging to terminal.
        log_to_directory: Force logging to file in log directory.

        If neither is set, behavior depends on ENV:
            - development → terminal
            - production → file
    """

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        return logger  # Avoid duplicate handlers

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] %(message)s"
    )

    # Determine where to log based on flags or ENV
    if LOG_TO_TERMINAL or (LOG_TO_TERMINAL is None and ENV == "development"):
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        if log_file is None:
            log_file = f"{name}.log"

        file_handler = TimedRotatingFileHandler(
            os.path.join(DEFAULT_LOG_DIR, log_file),
            when="midnight",
            backupCount=7,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Log directory should be %APP_DATA%/local
LOG_DIR = os.path.join(os.getenv("APPDATA", os.path.expanduser("~")), "FixLife", "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str, log_file: str = None, level=logging.INFO):
    if log_file is None:
        log_file = f"{name}.log"

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if logger.hasHandlers():
        return logger  # Prevent duplicate handlers

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] [%(name)s] %(message)s"
    )

    file_handler = TimedRotatingFileHandler(
        os.path.join(LOG_DIR, log_file),
        when="midnight",
        backupCount=7,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

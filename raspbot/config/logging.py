import logging
from logging.handlers import RotatingFileHandler

from .settings import DT_FORMAT, LOG_FORMAT, LOGS_DIR


def configure_logging(name: str) -> logging.Logger:
    """Logging configuration."""
    LOGS_DIR.mkdir(exist_ok=True)
    log_file = LOGS_DIR / name

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(fmt=LOG_FORMAT, datefmt=DT_FORMAT)
    rotating_handler = RotatingFileHandler(log_file, maxBytes=10**6, backupCount=5)
    rotating_handler.setFormatter(formatter)
    rotating_handler.setLevel(logging.INFO)
    logger.addHandler(rotating_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(logging.DEBUG)
    logger.addHandler(stream_handler)
    return logger

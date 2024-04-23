import functools
import logging
from logging.handlers import RotatingFileHandler

from raspbot.settings import settings


def configure_logging(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Logging configuration."""
    settings.LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    formatter = logging.Formatter(fmt=settings.LOG_FORMAT, datefmt=settings.LOG_DT_FMT)
    rotating_handler = RotatingFileHandler(
        filename=settings.LOG_FILE,
        maxBytes=settings.LOG_FILE_SIZE,
        backupCount=settings.LOG_FILES_TO_KEEP,
        encoding="UTF-8",
    )
    rotating_handler.setFormatter(formatter)
    rotating_handler.setLevel(settings.LOG_FILE_LEVEL)
    logger.addHandler(rotating_handler)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.setLevel(settings.LOG_STREAM_LEVEL)
    logger.addHandler(stream_handler)
    return logger


# Декоратор


def log(logger: logging.Logger = None):
    """Decorator for logging function calls, returns and raises."""
    if logger is None:
        logger = logging.get_logger(__name__)

    def decorator_log(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"Функция {func.__name__} вызвана с аргументами {signature}.")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Результат функции {func.__name__}: {result}")
                return result
            except Exception as e:
                logger.exception(
                    f"В функции {func.__name__} вызвано исключение: {str(e)}"
                )
                raise e

        return wrapper

    return decorator_log

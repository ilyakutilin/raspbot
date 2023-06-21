import functools
import logging
from logging.handlers import RotatingFileHandler

from raspbot.settings import settings


def configure_logging(name: str, level: int = logging.DEBUG) -> logging.Logger:
    """Logging configuration."""
    settings.LOG_DIR.mkdir(exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
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


def get_default_logger():
    return logging.get_logger(__name__)


def log(_func=None, *, my_logger: logging.Logger = None):
    def decorator_log(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if my_logger is None:
                logger = get_default_logger()
            else:
                logger = my_logger
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            signature = ", ".join(args_repr + kwargs_repr)
            logger.debug(f"Функция {func.__name__} вызвана с аргументами {signature}.")
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                logger.exception(
                    f"В функции {func.__name__} вызвано исключение: {str(e)}"
                )
                raise e

        return wrapper

    if _func is None:
        return decorator_log
    return decorator_log(_func)

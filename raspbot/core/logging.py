import functools
import inspect
import logging
from logging.handlers import RotatingFileHandler

from raspbot.settings import settings

logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)


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


def log(logger: logging.Logger | None = None):  # noqa: C901
    """Decorator for logging function calls, returns and raises."""
    if logger is None:
        logger = logging.getLogger(__name__)

    def decorator_log(func):
        def _get_signature(args, kwargs):
            args_repr = [repr(a) for a in args]
            kwargs_repr = [f"{k}={v!r}" for k, v in kwargs.items()]
            return ", ".join(args_repr + kwargs_repr)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            signature = _get_signature(args, kwargs)
            logger.debug(f"Function {func.__name__} is called with args {signature}.")
            try:
                result = await func(*args, **kwargs)
                logger.debug(f"Function {func.__name__} returned {result}")
                return result
            except Exception as e:
                logger.exception(
                    f"Exception {str(e)} was raised in function {func.__name__}."
                )
                raise e

        def sync_wrapper(*args, **kwargs):
            signature = _get_signature(args, kwargs)
            logger.debug(f"Function {func.__name__} is called with args {signature}.")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"Function {func.__name__} returned {result}")
                return result
            except Exception as e:
                logger.exception(
                    f"Exception {str(e)} was raised in function {func.__name__}."
                )
                raise e

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator_log

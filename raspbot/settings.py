from pathlib import Path

from pydantic_settings import BaseSettings

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = None
if Path.exists(BASE_DIR / ".env"):
    ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Project settings."""

    # Keys and tokens
    YANDEX_KEY: str
    TELEGRAM_TOKEN: str
    TELEGRAM_TESTENV_TOKEN: str = ""

    # Endpoints and Headers
    SEARCH_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/search/"
    STATIONS_LIST_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/stations_list/"
    COPYRIGHT_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/copyright/"
    API_EXCEPTION_THRESHOLD: int = 10
    API_EXCEPTION_WINDOW_MINUTES: int = 5

    # Files and directories
    FILES_DIR: str | Path = BASE_DIR / "files"

    # DB connection
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    LC_COLLATE: str = "ru_RU.UTF-8"
    LC_CTYPE: str = "ru_RU.UTF-8"

    # Email
    EMAIL_FROM: str
    EMAIL_HOST: str
    EMAIL_PORT: int
    EMAIL_USER: str
    EMAIL_PASSWORD: str
    EMAIL_TO: str

    # Telegram API
    MAX_TG_MSG_LENGTH: int = 4096

    # Timetables
    CLOSEST_DEP_LIMIT: int = 12
    DEP_FORMAT: str = "%H:%M"
    ROUTE_INLINE_DELIMITER: str = f" {chr(10145)} "
    ROUTE_INLINE_LIMIT: int = 38
    RECENT_FAV_LIST_LENGTH: int = 8
    INLINE_DEPARTURES_QTY: int = 4
    MAX_THREADS_FOR_LONG_FMT: int = 20
    MAX_DAYS_INTO_PAST: int = 0
    MAX_MONTHS_INTO_FUTURE: int = 11
    DAYS_BETWEEN_STATIONS_DB_UPDATE: int = 14

    # Logging
    LOG_FORMAT: str = (
        "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
    )
    LOG_DT_FMT: str = "%d.%m.%Y %H:%M:%S"
    LOG_STREAM_LEVEL: str = "INFO"
    LOG_FILE_LEVEL: str = "INFO"
    LOG_DIR: str | Path = BASE_DIR / "logs"
    LOG_FILE: str | Path = Path(LOG_DIR, "raspbot.log")
    LOG_FILE_SIZE: int = 10 * 2**20
    LOG_FILES_TO_KEEP: int = 5

    @property
    def headers(self) -> dict[str, str | bytes | None]:
        """Get headers for connection to Yandex API."""
        return {"Authorization": self.YANDEX_KEY}

    @property
    def database_url(self) -> str:
        """Get a link for connecting to DB."""
        return (
            "postgresql+asyncpg://"
            f"{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.POSTGRES_DB}"
        )

    class Config:
        """Settings config."""

        env_file = ENV_FILE


def get_settings():
    """Get project settings."""
    return Settings()


settings = get_settings()

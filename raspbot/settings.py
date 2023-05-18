from pathlib import Path

from pydantic import BaseSettings
from pydantic.tools import lru_cache

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = None
if Path.exists(BASE_DIR / ".env"):
    ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """Project settings."""

    # Keys and tokens
    YANDEX_KEY: str
    TELEGRAM_TOKEN: str
    TELEGRAM_CHAT_ID: str

    # Endpoints and Headers
    SEARCH_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/search/"
    SCHEDULE_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/schedule/"
    STATIONS_LIST_ENDPOINT: str = "https://api.rasp.yandex.net/v3.0/stations_list/"

    # Files and directories
    FILES_DIR: str | Path = BASE_DIR / "files"

    # DB connection
    POSTGRES_DB: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    DB_HOST: str
    DB_PORT: str

    # Logging
    LOG_FORMAT: str = (
        "%(asctime)s — %(name)s — %(levelname)s — %(funcName)s:%(lineno)d — %(message)s"
    )
    LOG_DT_FMT: str = "%d.%m.%Y %H:%M:%S"
    LOG_STREAM_LEVEL: str = "INFO"
    LOG_FILE_LEVEL: str = "INFO"
    LOG_DIR: str | Path = BASE_DIR / "logs"
    LOG_FILE: str = "raspbot.log"
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
        env_file = ENV_FILE


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()

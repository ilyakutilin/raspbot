import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Keys and tokens
YANDEX_KEY = os.getenv("YANDEX_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Endpoints and Headers
SEARCH_ENDPOINT = "https://api.rasp.yandex.net/v3.0/search/"
SCHEDULE_ENDPOINT = "https://api.rasp.yandex.net/v3.0/schedule/"
STATIONS_LIST_ENDPOINT = "https://api.rasp.yandex.net/v3.0/stations_list/"
HEADERS: dict[str, str | bytes | None] = {"Authorization": YANDEX_KEY}

# Files and directories
BASE_DIR = Path(__file__).parent.parent
FILES_DIR = BASE_DIR / "files"
LOGS_DIR = BASE_DIR / "logs"

# Logging
LOG_FORMAT = '"%(asctime)s - [%(levelname)s] - %(message)s"'
DT_FORMAT = "%d.%m.%Y %H:%M:%S"

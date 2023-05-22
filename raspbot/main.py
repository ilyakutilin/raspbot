from raspbot.db.stations.fill_db import populate_db
from raspbot.settings import settings

INITIAL_DATA = settings.FILES_DIR / "stations.json"
INITIAL_DATA_SAMPLE = settings.BASE_DIR / "config" / "sample.json"


def main():
    """Start."""
    populate_db(INITIAL_DATA)


main()

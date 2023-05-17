from raspbot.config.settings import settings
from raspbot.db.stations.process import populate_db

INITIAL_DATA = settings.FILES_DIR / "stations.json"
INITIAL_DATA_SAMPLE = settings.BASE_DIR / "config" / "sample.json"


def main():
    """Start."""
    populate_db(INITIAL_DATA)


main()

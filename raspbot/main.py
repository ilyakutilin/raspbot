from raspbot.config.constants import BASE_DIR, FILES_DIR
from raspbot.db.stations.process import populate_db

INITIAL_DATA = FILES_DIR / "stations.json"
INITIAL_DATA_SAMPLE = BASE_DIR / "config" / "sample.json"


def main():
    """Start."""
    populate_db(INITIAL_DATA)


main()

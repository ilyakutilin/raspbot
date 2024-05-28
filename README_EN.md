Telegram bot for searching the timetables of suburban trains in Russia.

The bot is based on the API of **Yandex Timetable** service.

Website: https://rasp.yandex.ru/

API documentation: https://yandex.ru/dev/rasp/doc/ru/

## Core functionality

- Search for timetables between two points. You can search between stations, settlements or mixed (for example, from Mokhovye Gory station to Nizhny Novgorod city). The reply will contain the nearest departures for the route
- Search the timetable for today / tomorrow / arbitrary date;
- View detailed information about a particular departure;
- Display information about the recent routes;
- Add routes to favorites.

## Implementation

- [Python 3.11](https://www.python.org/downloads/release/python-3110/)
- [Aiogram 3.5](https://docs.aiogram.dev/en/latest/)
- [PostgreSQL 16.1](https://www.postgresql.org/)
- [SQLAlchemy 2.0.13](https://www.sqlalchemy.org/)

The database is populated with information about stations, users and their routes (recent / favorite). Information about stations comes from API (it contains station/settlement codes that are necessary to generate endpoints for API requests). Due to the large size of the API response, information about stations is stored in the database.

By default, a scheduler is run together with the bot, which task is to receive an updated list of stations from API every two weeks and make necessary changes/additions to the database.

## Launch

Any method of launching the bot requires an API key for Yandex Timetable, a Telegram bot token, and a mailbox capable of sending e-mails via SMTP.

First steps:

Step 1. Get the [API key](https://yandex.ru/dev/rasp/doc/ru/concepts/access) of Yandex Timetable.

Step 2. [Create Telegram bot](https://core.telegram.org/bots/features#creating-a-new-bot) and get its token.

Step 3. Fill the `.env` file in the project root. Parameters marked with an asterisk `*` are mandatory.

### Docker

Preferred launch method.

You must install [Docker](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).

Next:

```bash
# Clone the project
git clone https://github.com/ilyakutilin/raspbot.git
# Go to the project folder
cd raspbot
# Set the following parameters in .env:
DB_HOST=db_raspbot
DB_PORT=5432
# Go to the folder with the Docker compose configuration for the database
cd infra/db
# Launch the PostgreSQL container
docker compose up -d
# Go to the Docker compose configuration folder for the bot
cd ../bot
# Launch the bot container
docker compose up -d --build
```

To [stop](https://docs.docker.com/reference/cli/docker/compose/stop/) containers, go to the appropriate folder (bot or db) and

```bash
docker compose stop
```

To [stop and delete](https://docs.docker.com/reference/cli/docker/compose/down/) a container:

```bash
docker compose down
```

For more information on using Docker go [here](https://docs.docker.com/reference/).

### Manual

- Deploy PostgreSQL database and fix its parameters in `.env`. For correct operation with the Russian language, `LC_COLLATE` and `LC_CTYPE` shall be set to `ru_RU.UTF-8`, and the database shall have [unaccent](https://www.postgresql.org/docs/current/unaccent.html) function [installed](https://www.postgresql.org/docs/current/sql-createextension.html) . Tested with PostgreSQL version [16](https://www.postgresql.org/about/news/postgresql-16-released-2715/).

- Install [Poetry](https://python-poetry.org/docs/#installation). Poetry [1.8](https://python-poetry.org/blog/announcing-poetry-1.8.0/) is recommended.

- Verify that Python `3.11` is available (you can use [Pyenv](https://github.com/pyenv/pyenv)). With `3.12` there are errors at launch, and `3.9` and less will not work due to the use of syntax that only appeared in `3.10` (`match`/`case`, type hints, etc.).

```bash
# Clone the project
git clone https://github.com/ilyakutilin/raspbot.git
# Go to the project folder
cd raspbot
# Activate the Poetry virtual environment
# https://python-poetry.org/docs/basic-usage/#activating-the-virtual-environment
poetry shell
# Install dependencies
# https://python-poetry.org/docs/basic-usage/#installing-dependencies
poetry install
# Go to the bot folder
cd raspbot
# Run migrations to create the database schema (database must be running and available)
alembic upgrade head
# Start the bot
python main.py
```

You can use optional keys when running the bot:

- `-t` start the bot in [test mode](https://core.telegram.org/bots/features#dedicated-test-environment). Before using test mode, you must create a separate instance of the bot in test environment, instruction [here](https://core.telegram.org/bots/features#creating-a-bot-in-the-test-environment).
- `-n` run the bot only, without a scheduler that tracks the relevance of station information in the database. In this case, it will be necessary to populate the database with station data before using the bot:

```bash
python db/stations/parse.py
```

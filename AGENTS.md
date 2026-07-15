# AGENTS.md

## Project Overview

Rasbot is an async Telegram bot that provides suburban train (электричка) timetables using the [Yandex Timetable API](https://yandex.ru/dev/rasp/). The UI and all messages are in **Russian**. Users search for routes between two points (station or settlement), view timetables, save favorites, and browse recent searches.

## Tech Stack

- **Language**: Python 3.11
- **Package manager**: uv (uv.lock, pyproject.toml)
- **Bot framework**: aiogram 3.5 (polling mode)
- **Database**: PostgreSQL 16 + SQLAlchemy 2.0 async (asyncpg) + Alembic migrations
- **Settings**: pydantic-settings, loaded from `.env` file
- **Scheduling**: APScheduler 3.x (for station DB periodic updates)
- **Email**: aiosmtplib + smtplib (admin error notifications)
- **Deployment**: Docker Compose (see `infra/` directory)

## Environment & Configuration

- `.env` file in project root (see `.env.example` for required vars)
- All settings loaded in `raspbot/settings.py` via pydantic-settings
- The `.env` file is NOT in the raspbot package — it's one level above. Settings searches for it at `BASE_DIR.parent / ".env"` first, then `BASE_DIR / ".env"`.
- Python version pinned in `.python-version`: 3.11

## Linting & Code Quality

- **Linter**: flake8 (config in `setup.cfg`, line length 88)
- **Formatter**: black (line length 88)
- **Import sorting**: isort (black profile, line length 88)
- **Type checker**: mypy (with SQLAlchemy plugin; currently commented out in pre-commit)
- **Pre-commit**: isort, black, flake8, autopep8, autoflake, plus generic hooks
- **Tests**: Test fixtures exist at `tests/fixtures/` (pytest), but currently have minimal/no test code

Run linting:
```bash
uv run flake8 raspbot/
uv run mypy raspbot/
```

## Project Structure

```
raspbot/
├── main.py                    # Entry point, CLI args: --test, --nomonitor
├── settings.py                # Pydantic BaseSettings from .env
├── alembic.ini                # Alembic config (migrations at db/migrations/)
│
├── core/
│   ├── base.py                # Re-exports all ORM models for Alembic
│   ├── logging.py             # configure_logging() + @log decorator
│   ├── exceptions.py          # All custom exceptions (hierarchy)
│   └── email.py               # Sync/async email sending for admin alerts
│
├── apicalls/
│   ├── base.py                # get_response() — generic HTTP GET via aiohttp
│   ├── search.py              # search_between_stations() — Yandex API search
│   └── copyright.py           # get_copyright() — API copyright info
│
├── db/
│   ├── base.py                # BaseORM, engine, async_session_factory
│   ├── models.py              # Re-exports all models
│   ├── crud.py                # CRUDBase abstract class
│   ├── stations/
│   │   ├── models.py          # PointORM, RegionORM, LastUpdatedORM
│   │   ├── schema.py          # Pydantic schemas for station data
│   │   ├── parse.py           # Yandex stations DB parser/populator
│   │   └── schedule.py        # APScheduler job: periodic station DB update check
│   ├── routes/
│   │   ├── crud.py            # CRUDPoints (by title, by ID), CRUDRoutes
│   │   └── schema.py          # PointResponsePD, RouteResponsePD, ThreadResponsePD
│   ├── users/
│   │   ├── models.py          # UserORM, RouteORM, RecentORM
│   │   └── crud.py            # CRUDUsers, CRUDRecents (favs are bool on RecentORM)
│   └── migrations/            # Alembic migrations (initial, unaccent extension)
│
├── bot/
│   ├── bot.py                 # get_bot(), start_bot() — Dispatcher + routers
│   ├── constants/
│   │   ├── states.py          # FSM States: RouteState, TimetableState
│   │   ├── messages.py        # All user-facing message strings (Russian)
│   │   ├── buttons.py         # Button labels and commands (Russian)
│   │   └── callback.py        # CallbackData factories for inline keyboards
│   ├── start/                 # /start command handler, keyboards, utils
│   ├── routes/                # Point selection flow (departure → destination)
│   ├── timetable/             # Timetable display, departure info, date selection
│   └── users/                 # /recent, /fav commands, favorites management
│
├── services/
│   ├── timetable.py           # Timetable class: fetches API, formats threads
│   ├── routes.py              # PointSelector, PointRetriever, RouteFinder, RouteRetriever
│   ├── users.py               # User/recent/fav DB operations
│   ├── deptime.py             # Parse user time input → find departure UID
│   ├── other_date.py          # Parse user date input → Timetable for that date
│   ├── copyright.py           # Formatted copyright attribution
│   ├── prettify_datetimes.py  # Date/time display formatting (Russian)
│   ├── endings.py             # Russian word endings by numeral
│   ├── split.py               # Split string lists to fit Telegram message limits
│   ├── strip.py               # HTML tag stripping
│   └── shorteners/            # Shorten point types, regions, route descriptions
│
├── infra/
│   ├── db/compose.yaml        # PostgreSQL 16.1-alpine container
│   └── bot/compose.yaml       # Bot container (builds from Dockerfile)
│
└── temp/                      # Temporary/scratch scripts (ignored by git)
```

## Architecture & Design Patterns

### Entry Point (`main.py`)

Runs asyncio. Creates bot, optionally starts APScheduler for station DB monitoring. Two modes:
- `--test`: Uses Telegram test environment token
- `--nomonitor`: No station DB update monitoring

### Bot Flow (FSM States)

1. **RouteState.selecting_departure_point** — User enters departure point name
2. **RouteState.selecting_destination_point** — User enters destination point name
3. **TimetableState.exact_departure_info** — Viewing timetable, can click/tap specific departure
4. **TimetableState.other_date** — User enters custom date for timetable

### Data Flow

1. User inputs point name → `PointSelector.select_points()` queries DB via `CRUDPoints.get_points_by_title()` (uses PostgreSQL `unaccent` for case/accent-insensitive search)
2. Found points displayed as inline keyboard → user picks one
3. `RouteFinder.get_or_create_route()` finds or creates route in DB, adds/updates user's recent
4. `Timetable` class fetches data from Yandex API via `search_between_stations()`, handles pagination, future-only departures, timezone
5. Results formatted by `FormattedThreadList` subclasses depending on point types (station/station, station/settlement, etc.)

### Database Models

- **PointORM** (stations/settlements): title, yandex_code, point_type, region_id, geo coordinates
- **RegionORM**: title, yandex_code, relationship → points
- **RouteORM**: departure_point_id, destination_point_id (unique constraint)
- **UserORM**: telegram_id (unique), name, profile fields
- **RecentORM**: user_id, route_id, count, favorite (bool) — same model for recents AND favorites; unique on (user_id, route_id)
- **LastUpdatedORM**: tracks station DB population dates

### API Integration

- `get_response()` in `apicalls/base.py` does all HTTP GET calls
- `search_between_stations()` builds URL, calls API, handles pagination
- API exception threshold monitoring: if >10 errors in 5 minutes → email admin
- Only suburban transport type (`TransportTypes.SUBURBAN`)

### Error Handling

- Custom exception hierarchy in `core/exceptions.py`
- Critical errors trigger email to admin via `send_email_async()`
- `@log` decorator on most service/API functions logs calls, returns, exceptions
- User-facing error message: `msg.ERROR` — generic "internal error" apology

## Key Conventions

- All async code. Use `async/await` throughout.
- ORM classes named with `ORM` suffix, auto-derive table names (e.g., `PointORM` → `points`)
- Pydantic response schemas named with `PD` suffix (e.g., `PointResponsePD`)
- CRUD classes named `CRUD<ModelName>` (e.g., `CRUDPoints`, `CRUDUsers`)
- `@log(logger)` decorator on most functions (supports both sync and async)
- Line length: 88 (matching black default)
- No comments unless necessary — use descriptive names
- `# noqa` used sparingly for import ordering and false positives

## Docker Deployment

Two separate compose files in `infra/`:
1. `docker compose -f infra/db/compose.yaml up -d` — PostgreSQL
2. `docker compose -f infra/bot/compose.yaml up -d` — Bot

Dockerfile uses multi-stage build: uv sync (builder) → slim runtime image with Russian locale.

On startup: `alembic upgrade head && python main.py`

## Common Commands

```bash
# Install deps
uv sync

# Run bot (dev)
uv run python raspbot/main.py

# Run bot in test mode (no station monitoring)
uv run python raspbot/main.py --test --nomonitor

# Run linting
uv run flake8 raspbot/
uv run mypy raspbot/

# Run pre-commit on all files
uv run pre-commit run --all-files

# Create DB migration
cd raspbot && uv run alembic revision --autogenerate -m "description"

# Apply migrations
cd raspbot && uv run alembic upgrade head

# Docker build + run
docker compose -f infra/db/compose.yaml up -d
docker compose -f infra/bot/compose.yaml up -d
```

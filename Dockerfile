FROM python:3.11 AS builder

RUN pip install poetry==1.8.2

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /raspbot

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --without dev --no-root --no-interaction --no-ansi && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.11-slim AS runtime

RUN apt-get update && \
    apt-get install -y locales && \
    sed -i -e 's/# ru_RU.UTF-8 UTF-8/ru_RU.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

ENV VIRTUAL_ENV=/raspbot/.venv \
    PATH="/raspbot/.venv/bin:$PATH"

WORKDIR /raspbot

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY ./.env ./
COPY raspbot/ ./

CMD alembic upgrade head && python main.py

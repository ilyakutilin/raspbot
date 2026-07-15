FROM python:3.11 AS builder

RUN pip install uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_CACHE_DIR=/tmp/uv_cache

WORKDIR /raspbot

COPY pyproject.toml uv.lock ./
RUN touch README.md

RUN uv sync --no-group dev --frozen --no-install-project && rm -rf $UV_CACHE_DIR

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

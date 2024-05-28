For English go [here](https://github.com/ilyakutilin/raspbot/blob/e2a2dafe56fb0b4362cc64b0d1f26740d15f76fd/README_EN.md).

Телеграм-бот для поиска расписаний пригородных электричек России.

Бот основан на API сервиса **Яндекс Расписания**.

Сайт: https://rasp.yandex.ru/

Документация API: https://yandex.ru/dev/rasp/doc/ru/

## Основной функционал

- Поиск расписания между двумя пунктами. Можно искать между станциями, между населенными пунктами или вперемешку (например, от станции Моховые горы в город Нижний Новгород). В ответ выдаются ближайшие отправления по маршруту;
- Поиск на сегодня / завтра / произвольную дату;
- Просмотр подробной информации о конкретном рейсе;
- Вывод информации о последних запрошенных маршрутах;
- Добавление маршрутов в избранное.

## Реализация

- [Python 3.11](https://www.python.org/downloads/release/python-3110/)
- [Aiogram 3.5](https://docs.aiogram.dev/en/latest/)
- [PostgreSQL 16.1](https://www.postgresql.org/)
- [SQLAlchemy 2.0.13](https://www.sqlalchemy.org/)

В базу данных заносятся сведения о станциях, пользователях и их маршрутах (последних / избранных). Информация о станциях приходит от API (там содержатся коды станций / населённых пунктов, которые используются для формирования эндпоинтов для запросов к API). Ввиду большого размера ответа API информация о станциях хранится в БД.

По умолчанию вместе с ботом запускается планировщик, который каждые две недели получает обновленный список станций от API и вносит необходиме изменения / добавления в БД.

## Запуск

Любой способ запуска предполагает наличие ключа API для Яндекс Раписаний, токена Telegram бота, а также почтового ящика, способного отправлять e-mail'ы по SMTP.

Первые шаги:

Шаг 1. Получить [API ключ](https://yandex.ru/dev/rasp/doc/ru/concepts/access) Яндекс расписаний.

Шаг 2. [Создать Telegram бота](https://core.telegram.org/bots/features#creating-a-new-bot) и получить его токен.

Шаг 3. Заполнить файл `.env` в корне проекта. Параметры, отмеченные звездочкой `*`, обязательны к заполнению.

### В Docker контейнерах

Предпочтительный способ запуска.

Необходимо установить [Docker](https://docs.docker.com/engine/install/) и [Docker Compose](https://docs.docker.com/compose/install/).

Далее:

```bash
# Склонировать проект
git clone https://github.com/ilyakutilin/raspbot.git
# Перейти в папку с проектом
cd raspbot
# Проставить следующие параметры в .env:
DB_HOST=db_raspbot
DB_PORT=5432
# Перейти в папку с конфигурацией Docker compose для базы данных
cd infra/db
# Поднять контейнер с PostgreSQL
docker compose up -d
# Перейти в папку с конфигурацией Docker compose для бота
cd ../bot
# Поднять контейнер с ботом
docker compose up -d --build
```

Чтобы [остановить](https://docs.docker.com/reference/cli/docker/compose/stop/) контейнеры, нужно перейти в соответствующую папку (bot или db) и

```bash
docker compose stop
```

Чтобы [остановить и удалить](https://docs.docker.com/reference/cli/docker/compose/down/) контейнер:

```bash
docker compose down
```

Более подробная информация по использованию Docker [здесь](https://docs.docker.com/reference/).

### Вручную

- Развернуть базу данных PostgreSQL и прописать ее параметры в `.env`. Для корректной работы с русским языком `LC_COLLATE` и `LC_CTYPE` должны быть `ru_RU.UTF-8`, и в БД должна быть [установлена](https://www.postgresql.org/docs/current/sql-createextension.html) функция [unaccent](https://www.postgresql.org/docs/current/unaccent.html). Работа проверена с версией PostgreSQL [16](https://www.postgresql.org/about/news/postgresql-16-released-2715/).

- Установить [Poetry](https://python-poetry.org/docs/#installation). Рекомендуется Poetry [1.8](https://python-poetry.org/blog/announcing-poetry-1.8.0/).

- Убедиться в наличии Python `3.11` (можно использовать [Pyenv](https://github.com/pyenv/pyenv)). С `3.12` возникают ошибки при запуске, а `3.9` и меньше не будут работать в связи с использованием синтаксиса, появившегося только в `3.10` (`match`/`case`, type hints и т.п.).

```bash
# Склонировать проект
git clone https://github.com/ilyakutilin/raspbot.git
# Перейти в папку с проектом
cd raspbot
# Активировать виртуальное окружение Poetry
# https://python-poetry.org/docs/basic-usage/#activating-the-virtual-environment
poetry shell
# Установить зависимости
# https://python-poetry.org/docs/basic-usage/#installing-dependencies
poetry install
# Перейти в папку с ботом
cd raspbot
# Запустить миграции для создания схемы БД (БД должна быть запущена и доступна)
alembic upgrade head
# Запустить бота
python main.py
```

При запуске бота можно использовать опциональные ключи:

- `-t` запуск бота в [тестовом режиме](https://core.telegram.org/bots/features#dedicated-test-environment). Перед использованием тестового режима необходимо создать отдельный экземпляр бота в тестовом пространстве, инструкция [здесь](https://core.telegram.org/bots/features#creating-a-bot-in-the-test-environment).
- `-n` запуск только бота, без планировщика, отслеживающего актуальность информации о станциях в БД. В этом случае перед непосредственным использованием бота необходимо будет заполнить БД данными о станциях:

```bash
python db/stations/parse.py
```

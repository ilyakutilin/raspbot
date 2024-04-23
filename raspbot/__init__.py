"""
A Telegram bot for showing Russian suburban trains timetable.
Телеграм-бот для показа расписания пригородных электричек России.


---------- EN ----------
Source of information is Yandex.Tmetable service (https://rasp.yandex.ru/).
API: https://yandex.ru/dev/rasp/

Bot is made with aiogram: https://github.com/aiogram/aiogram.

In order to speed up the queries, all the stations, settlements, their codes and
other related data are stored in the database. The database of choice is PostgreSQL,
connection is made via SQLAlchemy (https://www.sqlalchemy.org/).



---------- RU ----------
Источник информации: сервис Яндекс.Расписания (https://rasp.yandex.ru/).
API: https://yandex.ru/dev/rasp/

Бот сделан на библиотеке aiogram: https://github.com/aiogram/aiogram.

Для ускорения запросов, все станции, населенные пункты, их коды и другие связанные
данные хранятся в базе данных. Используется база данных PostgreSQL, подключение
осуществляется с помощью SQLAlchemy (https://www.sqlalchemy.org/).

"""

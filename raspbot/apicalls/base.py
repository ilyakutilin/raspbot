from http import HTTPStatus

import aiohttp
from dotenv import load_dotenv

from raspbot.core import exceptions as exc
from raspbot.core.logging import configure_logging

load_dotenv()

logger = configure_logging(__name__)


async def get_response(
    endpoint: str, headers: dict[str, str | bytes | None]
) -> dict | None:
    """
    Отправляет запрос на сервер и возвращает ответ.

    Принимает на вход:
        endpoint (строка): URL адрес (эндпоинт), по которому нуэно перейти;
        headers (словарь): Хедеры (напр. токен аутентификации для API).

    Вызывает исключения:
        EmptyHeadersError: вызывается при отсутствии хедеров;
        APIStatusCodeError: вызывается при плохом статус коде;
        APIConnectionError: вызывается при ошибках соединения.

    Возвращает:
        словарь или None: При получении ответа в виде JSON конвертирует его в словарь;
        в противном случае возвращает None.
    """
    if headers["Authorization"] is None:
        raise exc.EmptyHeadersError("Отсутствует ключ авторизации в хедере.")
    async with aiohttp.ClientSession() as session:
        try:
            logger.debug(f"Отправляю запрос на адрес {endpoint}.")
            response = await session.get(url=endpoint, headers=headers)
            if response.status != HTTPStatus.OK:
                raise exc.APIStatusCodeError(
                    f"Адрес {endpoint} недоступен - статус: "
                    f"{response.status} "
                    f"{HTTPStatus(response.status).phrase}. "
                )
        except Exception as e:
            raise exc.APIConnectionError(
                f"При соединении с эндпоинтом {endpoint} возникла ошибка. "
                f"Хедеры: {headers}. Описание ошибки: {e}"
            ) from e
        else:
            logger.debug(
                f"Запрос на эндпоинт {endpoint} был успешно осуществлен, "
                "получен ответ."
            )
            return await response.json(content_type=None)

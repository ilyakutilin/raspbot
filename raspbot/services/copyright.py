from raspbot.apicalls.copyright import get_copyright


async def get_formatted_copyright() -> str:
    """Generates formatted copyright message."""
    copyright_dict = await get_copyright()
    try:
        text = copyright_dict["copyright"]["text"]
        url = copyright_dict["copyright"]["url"]
    except (KeyError, TypeError):
        return (
            "Данные предоставлены сервисом Яндекс.Расписания (http://rasp.yandex.ru/)"
        )
    return f"{text} ({url})"

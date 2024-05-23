from raspbot.core.logging import configure_logging, log

logger = configure_logging(__name__)

special_cases = {
    "Еврейская автономная область": "ЕАО",
    "Кемеровская область - Кузбасс": "Кемеровская обл.",
    "Москва и Московская область": "МСК и МО",
    "Ненецкий автономный округ": "НАО",
    "Санкт-Петербург и Ленинградская область": "СПБ и ЛО",
    "Чукотский автономный округ": "ЧАО",
    "Ямало-Ненецкий автономный округ": "ЯНАО",
}

shorteners = {
    "область": "обл.",
    "Республика": "Респ.",
}


@log(logger)
def get_short_region_title(region_title: str) -> str:
    """
    Generates a short region title to fit the bot inline keyboard buttons.

    "Республика" is replaced with "Респ.", "область" with "обл.", and in some
    specific cases the region is abbreviated (e.g. "Москва и Московская область"
    replaced with "МСК и МО").

    Accepts:
        region_title (str): Full region title from the database.

    Returns:
        str: Short region title.
    """
    if region_title in special_cases:
        region_title = special_cases[region_title]
        return region_title
    region_title_split: list[str] = region_title.split()
    for element in region_title_split:
        if element in shorteners:
            short_element = shorteners[element]
            element_index = region_title_split.index(element)
            region_title_split[element_index] = short_element
    short_region_title = " ".join(region_title_split)
    return short_region_title


if __name__ == "__main__":
    print(get_short_region_title(input("Input title: ")))

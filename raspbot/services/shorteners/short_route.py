"""
Модуль для сокращения описания маршрута на инлайн-кнопках.

Пример: строка "Санкт-Петербург (Московский вокзал) ➡ Чудово-1 (Московское)"
не поместится на инлайн-кнопку бота целиком, на кнопке будет отображён только начальный
пункт маршрута, и выбор маршрута (например, из списка избранного) будет практически
невозможен. Такую строку нужно сокращать.
Результатом работы данного модуля станет строка "СПб (Моск вкз) ➡ Чудово-1 (Моск)",
которая поместится на кнопку.
"""

import re
from bisect import bisect_left

from raspbot.core.logging import configure_logging, log
from raspbot.settings import settings

logger = configure_logging(name=__name__)

DELIMITER = settings.ROUTE_INLINE_DELIMITER
ALPHABET = "а-яА-ЯёЁ"
CONSONANTS = "бвгджзйклмнпрстфхцчшщ"

SPECIAL_PHRASES = {
    r"ст\.": "ст.",
    r"г\.": "г.",
    r"\(\d+\sкм\)": "",
    r"\(бывш\..*?\)": "",
    r"Санкт-Петербург": "СПб",
    r"Нижний Новгород": "НН",
}

SPECIAL_WORDS = {
    r"км": "км",
    r"Москва": "Мск",
    r"Екатеринбург": "Екб",
    r"(?i)московск\w{1,2}": "моск",
    r"(?i)пассажирск\w{1,2}": "пасс",
    r"(?i)туристическ\w{1,2}": "тур",
    r"(?i)вокзал": "вкз",
    r"(?i)северн\w{1,2}": "сев",
    r"(?i)западн\w{1,2}": "зап",
    r"(?i)южн\w{1,2}": "южн",
    r"(?i)восточн\w{1,2}": "вост",
    r"(?i)товарн\w{1,2}": "тов",
    r"(?i)совхоз": "свх",
    r"(?i)аэропорт": "а/п",
}

SPECIAL_CASES = SPECIAL_PHRASES | SPECIAL_WORDS


@log(logger)
def _replace_special_phrases(
    string: str, special_phrases: dict[str | re.Pattern, str]
) -> str:
    """
    Заменяет определенные элементы строки на сокращенные в соответствии со словарём.

    Принимает на вход:
        string: строку, в которой нужно искать определенные элементы;
        - special_phrases: словарь элементов. Если в переданной строке встречается
          элемент из этого словаря, он заменяется на соответствующее сокращённое
          значение.

    Возвращает строку, в которой заменены словарные элементы, если они в ней
    встречаются.
    """
    modified_string = string
    for pattern, value in special_phrases.items():
        modified_string = re.sub(pattern, value, modified_string)
    return _clean_string(string=modified_string)


@log(logger)
def _clean_string(string: str) -> str:
    """
    Очищает строку от лишних пробелов.

    Принимает на вход строку.
    Возвращает строку без пробелов в начале и в конце, а также без лишних пробелов
    в середине.
    """
    cleaned_string = string.strip()
    return re.sub(r"\s+", " ", cleaned_string)


@log(logger)
def _split_string_into_tokens(string: str) -> list[str]:
    """
    Разделяет строку на токены.

    Принимает на вход строку.

    Возвращает список токенов, представляющих собой элементы изначальной строки.
    В отдельные токены объединяются следующие элементы строки:
    - слова (последовательность букв);
    - числа (последовательность цифр);
    - символ разделителя (отделяющего пункт отправления от пункта назначения в описании
      маршрута) с пробелами по бокам.
    Остальные символы (пробелы, запятые, точки, дефисы и т.п.) представляют собой
    отдельные токены.
    """
    tokens = re.findall(
        r"{delimiter}|\d+|[{alphabet}]+|[^{alphabet}\d]".format(
            delimiter=DELIMITER, alphabet=ALPHABET
        ),
        string,
    )
    return tokens


@log(logger)
def _distribute_tokens(
    tokens: list[str],
) -> tuple[list[tuple[int, str]], list[tuple[int, str]]]:
    """
    Распределяет токены по отдельным спискам по их содержимому.

    Принимает на вход список с токенами.

    Возвращает два списка:
    - В первом списке слова, которые мы потом будем сокращать;
    - Во втором списке всё остальное (т.е. токены, которые не подлежат сокращению и
      будут перенесены в финальное сокращённое описание маршрута без изменений.)
    К каждому токену добавляем его позицию в изначальном списке, чтобы потом можно было
    их в правильном порядке соединить в финальную строку. Таким образом, элементами
    каждого списка являются кортежи, состоящие из индекса позиции токена и
    непосредственно самого токена.
    """
    letters_list = []
    other_list = []
    position = 0

    for token in tokens:
        pattern = r"^[{}]+$".format(ALPHABET)
        if re.match(pattern, token) and token not in [
            value.lower() for value in SPECIAL_CASES.values()
        ]:
            letters_list.append((position, token))
        else:
            other_list.append((position, token))
        position += 1

    return letters_list, other_list


@log(logger)
def _take_closest(my_list: list[int], my_number: int) -> int:
    """
    Возвращает значение из списка my_list, ближайшее к my_number.

    Если числа одинаково близки, возвращает наименьшее.
    """
    pos = bisect_left(my_list, my_number)
    if pos == 0:
        return my_list[0]
    if pos == len(my_list):
        return my_list[-1]
    before = my_list[pos - 1]
    after = my_list[pos]
    if after - my_number < my_number - before:
        return after
    return before


@log(logger)
def _get_limit_multiplier(
    words: list[tuple[int, str]],
    others: list[tuple[int, str]],
    string_limit: int,
) -> float:
    """
    Определяет коэффициент сокращения слов в строке.

    Принимает на вход:
        - words: список кортежей, состоящих из индекса позиций в описании маршрута
          и токена (слова);
        others: список кортежей, состоящих из индекса позиции в описании маршрута
          и токена, не являющегося словом;
        string_limit: Лимит длины, к которому необходимо привести финальную строку.

    Возвращает коэффициент сокращения в формате числа с плавающей запятой,
    на который должны будут умножаться слова для достижения оптимальной длины
    сокращенной строки.
    """
    workable_limit = string_limit - sum(len(t[1]) for t in others)
    return min((workable_limit / sum(len(t[1]) for t in words)), 1)


@log(logger)
def _shorten_word(word: str, limit_multiplier: float) -> str:
    """
    Сокращает слово по установленным правилом в соответствии с лимитом.

    Принимает на вход:
        - word (str): слово, которое необходимо сократить
        - limit_multiplier (float): коэффициент, на который умножается длина слова
          для получения лимита его длины.

    Возвращает сокращённое слово.
    """
    # Если слово есть в словаре спец слов, то оно сокращается по значению словаря.
    for pattern in SPECIAL_WORDS:
        if re.match(pattern, word):
            if word[0].isupper() and "(?i)" in pattern:
                return SPECIAL_WORDS[pattern].capitalize()
            return SPECIAL_WORDS[pattern]

    # Если коэффициент сокращения больше или равен 1, то слово не сокращается.
    if limit_multiplier >= 1:
        logger.debug(f"Нет смысла сокращать слово {word}, оно и так помещается.")
        return word

    # Проверяем, есть ли в слове согласные. Если нет - возвращаем изначальное слово.
    if not any(char.lower() in CONSONANTS for char in word):
        logger.debug(f"В слове {word} нет согласных. Возвращаем слово целиком.")
        return word

    consonant_indices = [
        index for index, char in enumerate(word) if char.lower() in CONSONANTS
    ]
    logger.debug(f"Индексы согласных букв в слове {word}: {consonant_indices}")

    word_length = len(word)
    max_word_length = word_length * limit_multiplier

    last_consonant = _take_closest(my_list=consonant_indices, my_number=max_word_length)
    logger.debug(f"Последняя согласная в слове {word}: {last_consonant}")

    short_word = word[: last_consonant + 1]
    logger.debug(f"Сокращённое слово: {short_word}")

    if len(word) - len(short_word) == 1:
        logger.debug(
            f"Поскольку в слове {word} осталась только одна буква, не будем сокращать "
            f"до {short_word}, выведем полное слово."
        )
        return word

    return short_word


@log(logger)
def _combine(words: list[tuple[int, str]], others: list[tuple[int, str]]) -> str:
    """
    Комбинирует финальную строку из отдельных сокращённых токенов.

    Принимает на вход:
        - words: список кортежей, состоящих из индекса позиции в описании маршрута
          и токена (слова, сокращённого по установленным правилам);
        - others: список кортежей, состоящих из индекса позиции в описании маршрута
          и токена, не являющегося словом, при необходимости сокращённого
          по установленным правилам.

    Возвращает финальную сокращённую строку.
    """
    combined_list: list[tuple[int, str]] = words + others
    sorted_list: list[tuple[int, str]] = sorted(combined_list, key=lambda t: t[0])
    phrase_list: list[str] = [t[1] for t in sorted_list]
    сombined_title = _clean_string(string="".join(phrase_list))
    return сombined_title


@log(logger)
def shorten_route_description(route_descr: str, limit: int) -> str:
    """
    Сокращает описание маршрута, чтобы оно поместилось на inline кнопку бота.

    Принимает на вход:
        - route_descr: Строку с описанием маршрута
          (<Пункт отправления> <разделитель> <Пункт назначения>)
        limit (int): Лимит длины, к которому необходимо привести финальную строку.

    Возвращает сокращенное описание маршрута, помещающееся на inline кнопку бота.
    """
    route_descr = _replace_special_phrases(
        string=route_descr, special_phrases=SPECIAL_PHRASES
    )
    logger.debug(f"Описание после проверки на базовые паттерны и замены: {route_descr}")

    tokens = _split_string_into_tokens(string=route_descr)
    words, others = _distribute_tokens(tokens=tokens)
    logger.debug(
        "После разделения токенов на слова и прочие компоненты: слова - "
        f"{words}, прочее - {others}"
    )

    limit_multiplier = _get_limit_multiplier(
        words=words, others=others, string_limit=limit
    )
    logger.debug(f"Коэффициент лимита слов: {limit_multiplier}")

    words = [(t[0], _shorten_word(t[1], limit_multiplier)) for t in words]
    logger.debug(
        f"После сокращения слов получилось следующие токены: слова - {words}, "
        f"прочее - {others}"
    )

    short_route_descr = _combine(words=words, others=others)
    logger.debug(f"Длина сокращенного описания маршрута: {len(short_route_descr)}")
    return short_route_descr


if __name__ == "__main__":
    dep = input("Пункт отправления: ")
    dest = input("Пункт назначения: ")
    print(
        shorten_route_description(
            f"{dep}{DELIMITER}{dest}", settings.ROUTE_INLINE_LIMIT
        )
    )

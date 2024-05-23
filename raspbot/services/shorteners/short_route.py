"""
Module for shortening route description on inline buttons.

Example: the line "Санкт-Петербург (Московский вокзал) ➡ Чудово-1 (Московское)"
will not fit on the bot's inline keyboard button, only the starting point of the route
will be visible on the button, and it will be almost impossible to choose a route
(for example, from the favorites list). Such a string shall be shortened.
The result of this module will be the string "СПб (Моск вкз) ➡ Чудово-1 (Моск)",
which will fit the button.
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
    Replaces certain string elements with abbreviations according to the dictionary.

    Accepts:
        - string: the string in which to search for certain elements;
        - special_phrases: dictionary of elements.
          If an element from this dictionary is found in the passed string,
          it is replaced by the corresponding abbreviated value.

    Returns the string in which the dictionary elements are replaced, if found.
    """
    modified_string = string
    for pattern, value in special_phrases.items():
        modified_string = re.sub(pattern, value, modified_string)
    return _clean_string(string=modified_string)


@log(logger)
def _clean_string(string: str) -> str:
    """
    Clears the string of extra spaces.

    Accepts a string as input.
    Returns a string with no spaces at the beginning and end,
    and no extra spaces in the middle.
    """
    cleaned_string = string.strip()
    return re.sub(r"\s+", " ", cleaned_string)


@log(logger)
def _split_string_into_tokens(string: str) -> list[str]:
    """
    Splits a string into tokens.

    Accepts a string as input.

    Returns a list of tokens representing elements of the original string.
    The following string elements are combined into separate tokens:
    - words (a sequence of letters);
    - numbers (sequence of digits);
    - a separator character (separating the origin from the destination
      in the route description) with spaces on the sides.
    The remaining characters (spaces, commas, periods, hyphens, etc.)
    are treated as separate tokens.
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
    Distributes tokens to individual lists according to their contents.

    Takes a list with tokens as input.

    Returns two lists:
    - In the first list, the words that we are going to abbreviate later;
    - In the second list, everything else (i.e. tokens that are not to be abbreviated
      and will be moved to the final abbreviated route description without changes).
    To each token, we add its position in the original list, so that they can then be
    combined in the correct order into the final line. Thus, the elements of each list
    are tuples consisting of the token position index and the token itself.
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
    Returns the value from my_list closest to my_number.

    If the numbers are equally close, returns the smallest.
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
    Determines the reduction factor of words in a string.

    Takes as input:
        - words: a list of tuples consisting of the index of positions
          in the route description and a token (word);
        - other: a list of tuples consisting of a position index
          in the route description and a token that is not a word;
        - string_limit: The length limit which the final string should be reduced to.

    Returns the reduction factor (float), by which words will have to be multiplied
    to achieve the optimal length of the reduced string.
    """
    workable_limit = string_limit - sum(len(t[1]) for t in others)
    return min((workable_limit / sum(len(t[1]) for t in words)), 1)


@log(logger)
def _shorten_word(word: str, limit_multiplier: float) -> str:
    """
    Shortens a word by a set rule according to a limit.

    Takes as input:
        - word (str): the word to be shortened
        - limit_multiplier (float): the factor by which the length of the word
          is multiplied to get the limit of its length.

    Returns the shortened word.
    """
    # If a word is in the special words dict, it is abbreviated as per the dict value.
    for pattern in SPECIAL_WORDS:
        if re.match(pattern, word):
            if word[0].isupper() and "(?i)" in pattern:
                return SPECIAL_WORDS[pattern].capitalize()
            return SPECIAL_WORDS[pattern]

    # If a reduction coefficient is more than or equal to 1,
    # the word does not get shortened
    if limit_multiplier >= 1:
        logger.debug(f"No point in shortening the word '{word}', it fits as is.")
        return word

    # Check if there are consonants in the word. If not, return the original word.
    if not any(char.lower() in CONSONANTS for char in word):
        logger.debug(f"The word '{word}' has no consonants. Returning the whole word.")
        return word

    consonant_indices = [
        index for index, char in enumerate(word) if char.lower() in CONSONANTS
    ]
    logger.debug(f"indices of consonants in word '{word}': {consonant_indices}")

    word_length = len(word)
    max_word_length = word_length * limit_multiplier

    last_consonant = _take_closest(my_list=consonant_indices, my_number=max_word_length)
    logger.debug(f"The last consonant in word '{word}': {last_consonant}")

    short_word = word[: last_consonant + 1]
    logger.debug(f"The shortened word is '{short_word}'")

    if len(word) - len(short_word) == 1:
        logger.debug(
            f"Since there is only one letter left in word '{word}', there is no point "
            f"in shortening it to '{short_word}', so returning the whole word."
        )
        return word

    return short_word


@log(logger)
def _combine(words: list[tuple[int, str]], others: list[tuple[int, str]]) -> str:
    """
    Combines a final string of individual abbreviated tokens.

    Takes as input:
        - words: a list of tuples consisting of a position index
          in the route description and a token
          (a word abbreviated according to the established rules);
        - others: a list of tuples consisting of a position index
        in the route description and a token that is not a word,
        if necessary abbreviated according to the set rules.

    Returns the final abbreviated string.
    """
    combined_list: list[tuple[int, str]] = words + others
    sorted_list: list[tuple[int, str]] = sorted(combined_list, key=lambda t: t[0])
    phrase_list: list[str] = [t[1] for t in sorted_list]
    сombined_title = _clean_string(string="".join(phrase_list))
    return сombined_title


@log(logger)
def shorten_route_description(route_descr: str, limit: int) -> str:
    """
    Shortens the route description to fit on the bot's inline keyboard button.

    Accepts:
        - route_descr: A string containing the route description
          (<departure point> <separator> <destination point>)
        - limit (int): The length limit which the final string should be reduced to.

    Returns an abbreviated route description that fits on the bot's inline button.
    """
    route_descr = _replace_special_phrases(
        string=route_descr, special_phrases=SPECIAL_PHRASES
    )
    logger.debug(
        "Route description after checking for base patterns and replacements: "
        f"{route_descr}"
    )

    tokens = _split_string_into_tokens(string=route_descr)
    words, others = _distribute_tokens(tokens=tokens)
    logger.debug(
        "After splitting the tokens into words and other components: "
        f"{words=}, {others=}"
    )

    limit_multiplier = _get_limit_multiplier(
        words=words, others=others, string_limit=limit
    )
    logger.debug(f"Word limit multiplier: {limit_multiplier}")

    words = [(t[0], _shorten_word(t[1], limit_multiplier)) for t in words]
    logger.debug(f"Tokens after word shortening: {words=}, {others=}")

    short_route_descr = _combine(words=words, others=others)
    logger.debug(f"Length of the shortened route description: {len(short_route_descr)}")
    return short_route_descr


if __name__ == "__main__":
    dep = input("Пункт отправления: ")
    dest = input("Пункт назначения: ")
    print(
        shorten_route_description(
            f"{dep}{DELIMITER}{dest}", settings.ROUTE_INLINE_LIMIT
        )
    )

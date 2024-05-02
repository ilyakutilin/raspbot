def get_ending(num: int) -> str:
    """Get the ending for a Russian numeral."""
    if num % 100 in {11, 12, 13, 14}:
        return "ов"
    if num % 10 in {0, 5, 6, 7, 8, 9}:
        return "ов"
    if num % 10 in {2, 3, 4}:
        return "а"
    if num % 10 in {1}:
        return ""
    raise AssertionError("Unexpected error")


def days_with_ending(num: int) -> str:
    """Get the number of days with the Russian word for 'days' in correct form."""
    if num % 100 in {11, 12, 13, 14}:
        return f"{num} дней"
    if num % 10 in {0, 5, 6, 7, 8, 9}:
        return f"{num} дней"
    if num % 10 in {2, 3, 4}:
        return f"{num} дня"
    if num % 10 in {1}:
        return f"{num} день"
    raise AssertionError("Unexpected error")

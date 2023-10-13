def get_ending(num: int) -> str:
    if num % 100 in {11, 12, 13, 14}:
        return "ов"
    if num % 10 in {0, 5, 6, 7, 8, 9}:
        return "ов"
    if num % 10 in {2, 3, 4}:
        return "а"
    if num % 10 in {1}:
        return ""
    raise AssertionError("Unexpected error")

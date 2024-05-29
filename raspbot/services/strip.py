import re


def clean_text(text: str) -> str:
    """Removes all non-alphanumeric characters from the text."""
    pattern = re.compile(r"[^\w\sА-Яа-яёЁ]", re.UNICODE)
    cleaned_text = re.sub(pattern, "", text)
    cleaned_text = cleaned_text.strip()

    return cleaned_text

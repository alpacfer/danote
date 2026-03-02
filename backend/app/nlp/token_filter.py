from __future__ import annotations


def is_short_letter_word(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False

    letter_count = sum(1 for character in cleaned if character.isalpha())
    if letter_count == 0 or letter_count >= 3:
        return False

    return all(character.isalpha() or character in {"'", "’", "-"} for character in cleaned)


def is_wordlike_token(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    return any(character.isalnum() for character in cleaned)

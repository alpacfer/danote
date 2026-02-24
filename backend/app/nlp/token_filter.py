from __future__ import annotations


def is_wordlike_token(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    return any(character.isalnum() for character in cleaned)

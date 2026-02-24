from __future__ import annotations

from app.nlp.token_filter import is_wordlike_token


def test_is_wordlike_token_filters_symbols_and_keeps_words_numbers() -> None:
    assert is_wordlike_token("kan")
    assert is_wordlike_token("2")
    assert is_wordlike_token("gået")
    assert not is_wordlike_token("🙂")
    assert not is_wordlike_token(">")
    assert not is_wordlike_token("   ")

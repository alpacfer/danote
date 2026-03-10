from __future__ import annotations

from app.nlp.token_filter import is_short_letter_word, is_wordlike_token


def test_is_wordlike_token_filters_symbols_and_keeps_words_numbers() -> None:
    assert is_wordlike_token("kan")
    assert is_wordlike_token("2")
    assert is_wordlike_token("gået")
    assert not is_wordlike_token("🙂")
    assert not is_wordlike_token(">")
    assert not is_wordlike_token("   ")


def test_is_short_letter_word_flags_one_and_two_letter_words() -> None:
    assert is_short_letter_word("i")
    assert is_short_letter_word("to")
    assert is_short_letter_word("År")
    assert not is_short_letter_word("hus")
    assert not is_short_letter_word("2")
    assert not is_short_letter_word("a1")

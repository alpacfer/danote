from __future__ import annotations

from app.services.use_cases.wordbank.categories import is_allowed_word_category_label
from app.services.verification_support import is_valid_new_category


def test_is_allowed_word_category_label() -> None:
    # Strictly blocked solo labels
    assert not is_allowed_word_category_label("action")
    assert not is_allowed_word_category_label("Action")
    assert not is_allowed_word_category_label("nouns")
    assert not is_allowed_word_category_label("verb")
    assert not is_allowed_word_category_label("definite")
    assert not is_allowed_word_category_label("singular")

    # Allowed compound labels containing blocked words
    assert is_allowed_word_category_label("Action Movies")
    assert is_allowed_word_category_label("Common Nouns")
    assert is_allowed_word_category_label("Action Figure")
    assert is_allowed_word_category_label("Modal Verbs")

    # Standard allowed labels
    assert is_allowed_word_category_label("Geography")
    assert is_allowed_word_category_label("Animals and Plants")

    # Invalid cases
    assert not is_allowed_word_category_label("")
    assert not is_allowed_word_category_label(None)
    assert not is_allowed_word_category_label("This is a category label with way too many words in it")
    assert not is_allowed_word_category_label("a" * 45)  # too long
    assert not is_allowed_word_category_label("12345")  # non-alphabetic


def test_is_valid_new_category() -> None:
    # Strictly blocked solo labels
    assert not is_valid_new_category("action")
    assert not is_valid_new_category("Action")
    assert not is_valid_new_category("nouns")
    assert not is_valid_new_category("verb")
    assert not is_valid_new_category("definite")
    assert not is_valid_new_category("singular")

    # Allowed compound labels containing blocked words
    assert is_valid_new_category("Action Movies")
    assert is_valid_new_category("Common Nouns")
    assert is_valid_new_category("Action Figure")
    assert is_valid_new_category("Modal Verbs")

    # Standard allowed labels
    assert is_valid_new_category("Geography")
    assert is_valid_new_category("Animals and Plants")

    # Invalid cases
    assert not is_valid_new_category("")
    assert not is_valid_new_category("This is a category label with way too many words in it")
    assert not is_valid_new_category("a" * 45)  # too long
    assert not is_valid_new_category("12345")  # non-alphabetic

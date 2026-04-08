from __future__ import annotations

from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    WordTranslationFrame,
    cleanup_framed_word_translation,
)


def test_cleanup_framed_word_translation_reduces_noun_to_headword() -> None:
    frame = WordTranslationFrame(kind="noun", text="et vin")

    assert cleanup_framed_word_translation(frame, "in wine") == "wine"


def test_cleanup_framed_word_translation_keeps_multi_word_noun_phrase() -> None:
    frame = WordTranslationFrame(kind="noun", text="en glatis")

    assert cleanup_framed_word_translation(frame, "black ice") == "black ice"


def test_cleanup_framed_word_translation_normalizes_verb_to_infinitive() -> None:
    frame = WordTranslationFrame(kind="verb", text="at vande")

    assert cleanup_framed_word_translation(frame, "that the water") == "to water"


def test_cleanup_framed_word_translation_preserves_multi_word_verb_phrase() -> None:
    frame = WordTranslationFrame(kind="verb", text="at hedde")

    assert cleanup_framed_word_translation(frame, "to be called") == "to be called"


def test_cleanup_framed_word_translation_strips_adjective_scaffold() -> None:
    frame = WordTranslationFrame(kind="adjective", text="en tung ting")

    assert cleanup_framed_word_translation(frame, "a heavy thing") == "heavy"


def test_cleanup_framed_word_translation_strips_adverb_scaffold() -> None:
    frame = WordTranslationFrame(kind="adverb", text="han gør det hurtigt")

    assert cleanup_framed_word_translation(frame, "he does it quickly") == "quickly"


def test_cleanup_framed_word_translation_strips_adverb_scaffold_when_azure_reorders() -> None:
    # Azure often produces natural English word order ("he never does it")
    # rather than the frame-literal order ("he does it never").
    frame = WordTranslationFrame(kind="adverb", text="han gør det aldrig")

    assert cleanup_framed_word_translation(frame, "he never does it") == "never"


def test_cleanup_framed_word_translation_keeps_minimal_preposition_result() -> None:
    frame = WordTranslationFrame(kind="preposition", text="med huset")

    assert cleanup_framed_word_translation(frame, "with the house") == "with"


def test_cleanup_framed_word_translation_keeps_lexicalized_preposition_phrase() -> None:
    frame = WordTranslationFrame(kind="preposition", text="på grund af huset")

    assert cleanup_framed_word_translation(frame, "because of") == "because of"


def test_cleanup_framed_word_translation_keeps_lexicalized_conjunction_phrase() -> None:
    frame = WordTranslationFrame(kind="conjunction", text="selvom jeg går")

    assert cleanup_framed_word_translation(frame, "even though") == "even though"


def test_cleanup_framed_word_translation_reduces_article_to_token_only() -> None:
    frame = WordTranslationFrame(kind="article", text="en bog")

    assert cleanup_framed_word_translation(frame, "the book") == "the"


def test_cleanup_framed_word_translation_reduces_pronoun_to_token_only() -> None:
    frame = WordTranslationFrame(kind="pronoun", text="den er her")

    assert cleanup_framed_word_translation(frame, "it is here") == "it"


def test_cleanup_framed_word_translation_strips_proper_noun_label() -> None:
    frame = WordTranslationFrame(kind="proper_noun", text="navnet københavn")

    assert cleanup_framed_word_translation(frame, "name copenhagen") == "copenhagen"


def test_cleanup_framed_word_translation_strips_numeral_counted_noun() -> None:
    frame = WordTranslationFrame(kind="numeral", text="tre bøger")

    assert cleanup_framed_word_translation(frame, "three books") == "three"


def test_cleanup_framed_word_translation_rejects_uncertain_raw_phrase() -> None:
    frame = WordTranslationFrame(kind="raw", text="foo")

    assert cleanup_framed_word_translation(frame, "with the house") is None

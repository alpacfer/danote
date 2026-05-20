from __future__ import annotations

from pathlib import Path

import pytest

from app.db.migrations import get_connection
from app.services.use_cases.sentencebank import SentencebankUseCase
from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path
from tests.helpers.fakes import FakeTranslationService


def _translation_service() -> FakeTranslationService:
    return FakeTranslationService(
        {
            "hund": "dog",
            "hunden": "the dog",
            "mad": "food",
            "spise": "eat",
            "spiser": "eats",
        }
    )


def _lexeme_id_for_meaning(db_path: Path, meaning_id: int) -> int:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT lexeme_id FROM lexeme_meanings WHERE id = ?",
            (meaning_id,),
        ).fetchone()
    assert row is not None
    return int(row["lexeme_id"])


def _add_second_meaning(db_path: Path, lexeme_id: int) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO lexeme_meanings (
                lexeme_id,
                meaning_key,
                dictionary_status,
                gloss,
                english_translation,
                pos_tag,
                morphology
            )
            VALUES (?, 'manual-second-sense', 'generated_non_cor', 'animal group', 'dogs', 'NOUN', 'plural')
            """,
            (lexeme_id,),
        )
        assert cursor.lastrowid is not None
        meaning_id = int(cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, form, source, meaning_id)
            VALUES (?, 'hundene', 'observed', ?)
            """,
            (lexeme_id, meaning_id),
        )
        return meaning_id


def test_delete_last_meaning_deletes_lemma_and_unsaves_sentence_tokens(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank = WordbankUseCase(db_path, translation_service=_translation_service())
    sentencebank = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank,
        translation_service=_translation_service(),
    )

    saved_word = wordbank.add_word("Hunden", "hund")
    assert saved_word.meaning is not None
    meaning_id = saved_word.meaning.id

    sentence = sentencebank.add_sentence(
        "Hunden spiser mad",
        english_translation="The dog eats food",
    )
    linked_token = next(token for token in sentence.tokens if token.surface_form == "Hunden")
    assert linked_token.save_status == "saved"
    assert linked_token.meaning_id == meaning_id

    assert wordbank.delete_meaning(meaning_id) is True

    with pytest.raises(LookupError):
        wordbank.get_lemma_details("hund")

    refetched = sentencebank._repository.get_sentence(sentence.id)
    assert refetched is not None
    token = next(token for token in refetched.tokens if token.surface_form == "Hunden")
    assert token.save_status == "unsaved"
    assert token.lexeme_id is None
    assert token.meaning_id is None
    assert token.stored_lemma is None
    assert token.cor_id is None


def test_delete_one_meaning_keeps_multi_meaning_lemma(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank = WordbankUseCase(db_path, translation_service=_translation_service())
    sentencebank = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank,
        translation_service=_translation_service(),
    )

    saved_word = wordbank.add_word("Hunden", "hund")
    assert saved_word.meaning is not None
    first_meaning_id = saved_word.meaning.id
    lexeme_id = _lexeme_id_for_meaning(db_path, first_meaning_id)
    second_meaning_id = _add_second_meaning(db_path, lexeme_id)

    sentence = sentencebank.add_sentence(
        "Hunden spiser mad",
        english_translation="The dog eats food",
    )
    linked_token = next(token for token in sentence.tokens if token.surface_form == "Hunden")
    assert linked_token.meaning_id == first_meaning_id

    assert wordbank.delete_meaning(first_meaning_id) is False

    details = wordbank.get_lemma_details("hund")
    assert [section.id for section in details.meaning_sections] == [second_meaning_id]

    refetched = sentencebank._repository.get_sentence(sentence.id)
    assert refetched is not None
    token = next(token for token in refetched.tokens if token.surface_form == "Hunden")
    assert token.save_status == "unsaved"
    assert token.meaning_id is None


def test_delete_sentence_with_meanings_only_deletes_sentence_exclusive_meanings(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank = WordbankUseCase(db_path, translation_service=_translation_service())
    sentencebank = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank,
        translation_service=_translation_service(),
    )

    saved_word = wordbank.add_word("spiser", "spise")
    assert saved_word.meaning is not None
    meaning_id = saved_word.meaning.id

    first = sentencebank.add_sentence("spiser mad", english_translation="eats food")
    second = sentencebank.add_sentence("spiser", english_translation="eats")
    assert any(token.meaning_id == meaning_id for token in first.tokens)
    assert any(token.meaning_id == meaning_id for token in second.tokens)

    sentencebank.delete_sentence(first.id, delete_meanings=True)
    assert sentencebank._repository.get_sentence(first.id) is None
    assert wordbank.get_lemma_details("spise").lemma == "spise"

    sentencebank.delete_sentence(second.id, delete_meanings=True)
    assert sentencebank._repository.get_sentence(second.id) is None
    with pytest.raises(LookupError):
        wordbank.get_lemma_details("spise")


def test_delete_sentence_without_meanings_keeps_wordbank_entries(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    wordbank = WordbankUseCase(db_path, translation_service=_translation_service())
    sentencebank = SentencebankUseCase(
        db_path,
        wordbank_use_case=wordbank,
        translation_service=_translation_service(),
    )

    saved_word = wordbank.add_word("spiser", "spise")
    assert saved_word.meaning is not None
    sentence = sentencebank.add_sentence("spiser mad", english_translation="eats food")

    sentencebank.delete_sentence(sentence.id, delete_meanings=False)

    assert sentencebank._repository.get_sentence(sentence.id) is None
    assert wordbank.get_lemma_details("spise").lemma == "spise"

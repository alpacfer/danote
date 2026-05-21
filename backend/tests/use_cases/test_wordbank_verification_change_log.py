from __future__ import annotations

from pathlib import Path

from app.db.migrations import get_connection
from app.db.repositories.wordbank import WordbankRepository
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.use_cases.wordbank.verification_change_log import (
    build_change_log_before_json,
    query_surface_forms_snapshot,
    revert_fix_translation,
    revert_fix_variations,
)
from tests.helpers.factories import _db_path
from tests.helpers.fakes import FakeVerificationService


def _setup_word(db_path: Path, lemma: str = "løbe", translation: str = "to run") -> tuple[int, int]:
    """Add a word via search_seed and return (lexeme_id, meaning_id)."""
    use_case = WordbankUseCase(db_path)
    use_case.add_word(
        lemma,
        lemma,
        search_seed={
            "lemma": lemma,
            "surface": lemma,
            "cor_id": f"COR.{lemma.upper()}.1",
            "cor_lemma_idx": 1,
            "meaning_key": lemma,
            "gloss": translation,
            "english_translation": translation,
            "pos_tag": "VERB",
            "morphology": None,
        },
    )
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(lemma)
    assert lexeme is not None
    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT id FROM lexeme_meanings WHERE lexeme_id = ? LIMIT 1",
            (lexeme.id,),
        ).fetchone()
    assert meaning_row is not None
    return lexeme.id, int(meaning_row["id"])


def test_query_surface_forms_snapshot_returns_forms(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe")
    forms = query_surface_forms_snapshot(db_path, lexeme_id=lexeme_id, meaning_id=meaning_id)
    assert any(f["form"] == "løbe" for f in forms)


def test_build_change_log_before_json_fix_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _setup_word(db_path, "løbe", translation="to run")
    before = build_change_log_before_json(
        action_type="fix_translation",
        meaning_id=None,
        before_snapshot={"lemma": {"english_translation": "to run"}, "meaning": None},
        pre_apply_surfaces=None,
    )
    assert before["english_translation"] == "to run"
    assert before["action_type"] == "fix_translation"
    assert before["meaning_id"] is None


def test_build_change_log_before_json_fix_translation_with_meaning(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    before = build_change_log_before_json(
        action_type="fix_translation",
        meaning_id=meaning_id,
        before_snapshot={"lemma": {"english_translation": "to run"}, "meaning": {"english_translation": "to run"}},
        pre_apply_surfaces=None,
    )
    assert before["english_translation"] == "to run"
    assert before["meaning_id"] == meaning_id


def test_build_change_log_before_json_fix_variations(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe")
    surfaces = query_surface_forms_snapshot(db_path, lexeme_id=lexeme_id, meaning_id=meaning_id)
    before = build_change_log_before_json(
        action_type="fix_variations",
        meaning_id=meaning_id,
        before_snapshot={"lemma": {"lemma": "løbe"}, "meaning": None},
        pre_apply_surfaces=surfaces,
    )
    assert before["action_type"] == "fix_variations"
    assert "surface_forms" in before
    assert any(f["form"] == "løbe" for f in before["surface_forms"])


def test_revert_fix_translation_restores_lexeme_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id = _setup_word(db_path, "løbe", translation="to run")[0]
    # Simulate a change: update translation on the lexeme directly
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE lexemes SET english_translation = ? WHERE id = ?",
            ("to walk", lexeme_id),
        )
    # Revert
    revert_fix_translation(
        db_path=db_path,
        stored_lemma="løbe",
        meaning_id=None,
        old_translation="to run",
    )
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    assert lexeme.english_translation == "to run"


def test_revert_fix_translation_restores_meaning_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    # Simulate a change: update translation on the meaning
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE lexeme_meanings SET english_translation = ? WHERE id = ?",
            ("to walk", meaning_id),
        )
    # Revert
    revert_fix_translation(
        db_path=db_path,
        stored_lemma="løbe",
        meaning_id=meaning_id,
        old_translation="to run",
    )
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM lexeme_meanings WHERE id = ?",
            (meaning_id,),
        ).fetchone()
    assert row is not None
    assert row["english_translation"] == "to run"


def test_revert_fix_variations_restores_surface_forms(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe")

    # Snapshot original surface forms
    original_surfaces = query_surface_forms_snapshot(db_path, lexeme_id=lexeme_id, meaning_id=meaning_id)
    assert len(original_surfaces) >= 1

    # Simulate a change: delete all surface forms for this meaning
    with get_connection(db_path) as conn:
        conn.execute(
            "DELETE FROM surface_forms WHERE lexeme_id = ? AND meaning_id = ?",
            (lexeme_id, meaning_id),
        )

    # Verify deletion
    after_delete = query_surface_forms_snapshot(db_path, lexeme_id=lexeme_id, meaning_id=meaning_id)
    assert len(after_delete) == 0

    # Revert
    revert_fix_variations(
        db_path=db_path,
        stored_lemma="løbe",
        meaning_id=meaning_id,
        surface_forms_snapshot=original_surfaces,
    )

    # Verify restoration
    restored = query_surface_forms_snapshot(db_path, lexeme_id=lexeme_id, meaning_id=meaning_id)
    assert len(restored) == len(original_surfaces)
    assert any(f["form"] == "løbe" for f in restored)


def _insert_saved_sentence_token(
    db_path: Path,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    surface_form: str,
    english_translation: str,
) -> int:
    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO sentence_bank (
                owner_user_id, source_sentence, normalized_sentence, english_translation, translation_provider
            )
            VALUES (1, ?, ?, ?, ?)
            """,
            (f"jeg {surface_form}", f"jeg {surface_form}", "i run", "test"),
        )
        sentence_id = int(cursor.lastrowid or 0)
        cursor = conn.execute(
            """
            INSERT INTO sentence_bank_tokens (
                sentence_id, token_index, surface_form, normalized_surface,
                stored_lemma, lexeme_id, meaning_id, english_translation, save_status
            )
            VALUES (?, 1, ?, ?, ?, ?, ?, ?, 'saved')
            """,
            (
                sentence_id,
                surface_form,
                surface_form,
                "løbe",
                lexeme_id,
                meaning_id,
                english_translation,
            ),
        )
        return int(cursor.lastrowid or 0)


def _read_token_translation(db_path: Path, token_id: int) -> str | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT english_translation FROM sentence_bank_tokens WHERE id = ?",
            (token_id,),
        ).fetchone()
    return row["english_translation"] if row is not None else None


def test_fix_translation_propagates_to_saved_sentence_tokens(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    token_id = _insert_saved_sentence_token(
        db_path,
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        surface_form="løber",
        english_translation="to run",
    )

    use_case = WordbankUseCase(
        db_path,
        verification_service=FakeVerificationService(
            verdict="flagged",
            message="Wrong translation",
            actions=[{"action_type": "fix_translation", "english_translation": "to walk", "reason": "more accurate"}],
        ),
    )
    use_case.verify_added_word("løbe", None, meaning_id=meaning_id)

    assert _read_token_translation(db_path, token_id) == "to walk"


def test_revert_fix_translation_restores_sentence_token_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    token_id = _insert_saved_sentence_token(
        db_path,
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        surface_form="løber",
        english_translation="to run",
    )

    # Simulate an applied fix that changed both the meaning and the token
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE lexeme_meanings SET english_translation = ? WHERE id = ?",
            ("to walk", meaning_id),
        )
        conn.execute(
            "UPDATE sentence_bank_tokens SET english_translation = ? WHERE id = ?",
            ("to walk", token_id),
        )

    revert_fix_translation(
        db_path=db_path,
        stored_lemma="løbe",
        meaning_id=meaning_id,
        old_translation="to run",
    )

    assert _read_token_translation(db_path, token_id) == "to run"


def test_replace_lexeme_meaning_translation_propagates_to_sentence_tokens(tmp_path: Path) -> None:
    """Repository-level meaning translation update must refresh denormalized sentence tokens.

    This is the path used by contextual translation (sentence save) and find-alternative-
    translations; previously this path silently left sentence_bank_tokens.english_translation
    stale, so the sentence page kept the old translation even after the meaning had changed.
    """
    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    token_id = _insert_saved_sentence_token(
        db_path,
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        surface_form="løber",
        english_translation="to run",
    )

    repository = WordbankRepository(db_path)
    repository.replace_lexeme_meaning_translation(
        meaning_id=meaning_id,
        english_translation="to jog",
    )

    assert _read_token_translation(db_path, token_id) == "to jog"


def test_replace_lexeme_translation_propagates_to_lemma_scoped_sentence_tokens(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id, _meaning_id = _setup_word(db_path, "løbe", translation="to run")
    # Insert a lemma-scoped token (meaning_id IS NULL)
    token_id = _insert_saved_sentence_token(
        db_path,
        lexeme_id=lexeme_id,
        meaning_id=None,
        surface_form="løber",
        english_translation="to run",
    )

    repository = WordbankRepository(db_path)
    repository.replace_lexeme_translation(
        lexeme_id=lexeme_id,
        english_translation="to jog",
        provider="test",
    )

    assert _read_token_translation(db_path, token_id) == "to jog"


def test_fix_translation_propagates_via_batch_sentence_token_verification(tmp_path: Path) -> None:
    """End-to-end test: save sentence -> run batch verification -> re-fetch sentence -> assert token updated."""
    from app.db.repositories.sentencebank import SentencebankRepository, SentenceTokenWriteRecord
    from app.services.use_cases.sentencebank_token_persistence import (
        batch_verify_new_sentence_tokens,
    )

    db_path = _db_path(tmp_path)
    lexeme_id, meaning_id = _setup_word(db_path, "løbe", translation="to run")

    # Insert a sentence with a saved token referencing meaning_id
    sentencebank = SentencebankRepository(db_path)
    sentence_id = sentencebank.insert_sentence(
        source_text="jeg løber",
        normalized_sentence="jeg løber",
        english_translation="i run",
        translation_provider="test",
    )
    sentencebank.replace_sentence_tokens(
        sentence_id=sentence_id,
        tokens=[
            SentenceTokenWriteRecord(
                token_index=1,
                surface_form="løber",
                normalized_surface="løber",
                lemma_candidate="løbe",
                stored_lemma="løbe",
                lexeme_id=lexeme_id,
                meaning_id=meaning_id,
                cor_id=None,
                pos_tag="VERB",
                morphology=None,
                gloss=None,
                english_translation="to run",
                gloss_translation=None,
            ),
        ],
    )

    # Build a use case with a fake verification service that returns flagged fix_translation
    use_case = WordbankUseCase(
        db_path,
        verification_service=_BatchFakeVerificationService(
            verdict="flagged",
            english_translation="to walk",
        ),
    )

    # Run the actual batch verification path used by verify_sentence_tokens
    batch_verify_new_sentence_tokens(
        use_case.runtime,
        new_token_metadata=[
            {
                "stored_lemma": "løbe",
                "stored_surface_form": None,
                "meaning_id": meaning_id,
            },
        ],
        sentence_context="jeg løber",
    )

    # Re-fetch the sentence and assert the denormalized token translation is updated
    sentence = sentencebank.get_sentence(sentence_id)
    assert sentence is not None
    token = next(t for t in sentence.tokens if t.token_index == 1)
    assert token.english_translation == "to walk", (
        f"Token english_translation still stale: {token.english_translation!r}. "
        f"The propagation did not fire from the batch verification path."
    )


class _BatchFakeVerificationService:
    """Fake verification service that returns a flagged fix_translation for batch verification."""

    provider = "gemini"
    reviewer_role = "Professional Danish Language Expert"

    def __init__(self, verdict: str, english_translation: str) -> None:
        self._verdict = verdict
        self._english_translation = english_translation

    def verify_word_entry(self, payload):
        from app.services.verification import WordVerificationAction, WordVerificationResult
        return WordVerificationResult(
            verdict=self._verdict,
            message="Review needed",
            composed_word_count=1,
            problem="Wrong translation",
            change_to_implement="Use the correct verb",
            suggested_actions=(
                WordVerificationAction(
                    action_type="fix_translation",
                    english_translation=self._english_translation,
                    reason="more accurate",
                ),
            ),
        )

    def verify_word_entries_batch(self, payloads, sentence_context=None):
        return [self.verify_word_entry(p) for p in payloads]

    def classify_word_categories(self, payload):
        class Result:
            categories = ()
        return Result()


def test_auto_apply_fix_translation_on_verify(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _, meaning_id = _setup_word(db_path, "løbe", translation="to run")
    use_case = WordbankUseCase(
        db_path,
        verification_service=FakeVerificationService(
            verdict="flagged",
            message="Wrong translation",
            actions=[{"action_type": "fix_translation", "english_translation": "to walk", "reason": "more accurate"}],
        ),
    )
    use_case.verify_added_word("løbe", None, meaning_id=meaning_id)

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT english_translation FROM lexeme_meanings WHERE id = ?",
            (meaning_id,),
        ).fetchone()
    assert meaning_row is not None
    assert meaning_row["english_translation"] == "to walk"

    repository = WordbankRepository(db_path)
    # Change log was written
    entries = repository.get_change_log_entries_for_lemma("løbe")
    assert len(entries) == 1
    assert entries[0].action_type == "fix_translation"
    assert entries[0].meaning_id == meaning_id
    assert entries[0].reverted_at is None

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

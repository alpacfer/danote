from __future__ import annotations

import json
from pathlib import Path

from app.db.migrations import get_connection
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.use_cases.wordbank.pronunciation_repair import (
    find_missing_pronunciation_forms,
    queue_missing_pronunciations,
)
from tests.helpers.factories import _db_path
from tests.helpers.fakes import FakeTTSService


def test_find_missing_pronunciation_forms_includes_missing_root_and_partial_surface_audio(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        tts_service=FakeTTSService({"bog": b"lemma-wav", "bogen": b"surface-wav"}),
    )

    added = use_case.add_word("bogen", "bog")
    use_case.process_queued_pronunciations("bog", requested_forms=["bog", "bogen"])

    with get_connection(db_path) as conn:
        lexeme_id = int(conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("bog",)).fetchone()["id"])
        second_meaning_cursor = conn.execute(
            """
            INSERT INTO lexeme_meanings (
                lexeme_id,
                meaning_key,
                gloss,
                english_translation,
                pos_tag,
                morphology
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                lexeme_id,
                "swamp",
                "swamp",
                "swamp",
                "NOUN",
                "Gender=Com|Number=Sing|Definite=Def",
            ),
        )
        second_meaning_id = int(second_meaning_cursor.lastrowid)
        conn.execute(
            """
            INSERT INTO surface_forms (
                lexeme_id,
                meaning_id,
                form,
                source,
                seen_count,
                last_seen_at,
                pos_tag,
                morphology
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (
                lexeme_id,
                second_meaning_id,
                "bogen",
                "manual",
                1,
                "NOUN",
                "Gender=Com|Number=Sing|Definite=Def",
            ),
        )
        conn.execute(
            """
            UPDATE surface_forms
            SET pronunciation_audio = NULL,
                pronunciation_mime_type = NULL,
                pronunciation_provider = NULL,
                pronunciation_model = NULL,
                pronunciation_generated_at = NULL
            WHERE lexeme_id = ?
              AND form = ?
              AND meaning_id IS NULL
            """,
            (lexeme_id, "bog"),
        )

    assert added.queued_pronunciation_forms == ["bog", "bogen"]
    assert find_missing_pronunciation_forms(db_path) == {"bog": ["bog", "bogen"]}


def test_queue_missing_pronunciations_merges_forms_under_one_lemma_job(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        tts_service=FakeTTSService({"bog": b"lemma-wav", "bogen": b"surface-wav"}),
    )

    use_case.add_word("bogen", "bog")

    summary = queue_missing_pronunciations(db_path)

    assert summary.lemma_count == 1
    assert summary.form_count == 2
    assert summary.enqueued_jobs == 0
    assert summary.unchanged_jobs == 1
    assert summary.queued_forms_by_lemma == {"bog": ["bog", "bogen"]}

    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT dedupe_key, payload_json, status
            FROM wordbank_background_jobs
            WHERE job_type = 'generate_pronunciation'
            LIMIT 1
            """
        ).fetchone()

    assert row is not None
    assert str(row["dedupe_key"]) == "generate_pronunciation::bog"
    assert str(row["status"]) == "pending"
    assert json.loads(str(row["payload_json"])) == {
        "force": False,
        "requested_forms": ["bog", "bogen"],
        "stored_lemma": "bog",
    }

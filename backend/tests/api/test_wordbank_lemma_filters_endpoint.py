from __future__ import annotations

from fastapi.testclient import TestClient

from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from tests.api.wordbank_test_support import build_test_settings


def test_list_lemmas_returns_filter_metadata_for_all_meanings(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lexemes (lemma, english_translation, pos_tag, dictionary_status)
            VALUES ('drille', NULL, NULL, 'generated_non_cor')
            """
        )
        lexeme_id = int(conn.execute("SELECT id FROM lexemes WHERE lemma = 'drille'").fetchone()["id"])
        conn.execute(
            """
            INSERT INTO lexeme_meanings (
                lexeme_id, meaning_key, english_translation, pos_tag, dictionary_status
            ) VALUES (?, 'drille-verb', 'tease', 'VERB', 'generated_non_cor')
            """,
            (lexeme_id,),
        )
        verb_meaning_id = int(
            conn.execute("SELECT id FROM lexeme_meanings WHERE meaning_key = 'drille-verb'").fetchone()["id"]
        )
        conn.execute(
            """
            INSERT INTO lexeme_meanings (
                lexeme_id, meaning_key, english_translation, pos_tag, dictionary_status
            ) VALUES (?, 'drille-noun', 'tease', 'NOUN', 'generated_non_cor')
            """,
            (lexeme_id,),
        )
        noun_meaning_id = int(
            conn.execute("SELECT id FROM lexeme_meanings WHERE meaning_key = 'drille-noun'").fetchone()["id"]
        )
        conn.execute(
            "UPDATE lexeme_meanings SET english_translation = 'prank' WHERE id = ?",
            (noun_meaning_id,),
        )
        conn.executemany(
            """
            INSERT INTO wordbank_additional_translations (
                lexeme_id, meaning_id, english_translation, source
            ) VALUES (?, ?, ?, 'test')
            """,
            [
                (lexeme_id, verb_meaning_id, "mock"),
                (lexeme_id, verb_meaning_id, "Tease"),
            ],
        )
        conn.execute(
            """
            INSERT INTO surface_forms (lexeme_id, meaning_id, form, source, pos_tag)
            VALUES (?, ?, 'driller', 'observed', 'VERB')
            """,
            (lexeme_id, verb_meaning_id),
        )
        _assign_category(conn, lexeme_id=lexeme_id, meaning_id=None, label="School")
        _assign_category(conn, lexeme_id=lexeme_id, meaning_id=verb_meaning_id, label="Work")
        _assign_category(conn, lexeme_id=lexeme_id, meaning_id=noun_meaning_id, label="People")

    with TestClient(app) as client:
        response = client.get("/api/wordbank/lemmas")

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["lemma"] == "drille"
    assert item["pos_tags"] == ["NOUN", "VERB"]
    assert item["categories"] == ["People", "School", "Work"]
    assert item["english_translation"] is None
    assert item["translation_groups"] == [
        {
            "english_translation": "tease",
            "additional_translations": ["mock"],
        },
        {
            "english_translation": "prank",
            "additional_translations": [],
        },
    ]


def test_list_lemmas_returns_root_translation_groups_and_omits_empty_groups(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO lexemes (lemma, english_translation, pos_tag, dictionary_status)
            VALUES ('plante', 'plant', 'NOUN', 'generated_non_cor')
            """
        )
        plant_id = int(conn.execute("SELECT id FROM lexemes WHERE lemma = 'plante'").fetchone()["id"])
        conn.execute(
            """
            INSERT INTO wordbank_additional_translations (
                lexeme_id, meaning_id, english_translation, source
            ) VALUES (?, NULL, 'flora', 'test')
            """,
            (plant_id,),
        )
        conn.execute(
            """
            INSERT INTO lexemes (lemma, english_translation, pos_tag, dictionary_status)
            VALUES ('ukendt', NULL, NULL, 'unknown')
            """
        )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/lemmas")

    assert response.status_code == 200
    by_lemma = {item["lemma"]: item for item in response.json()["items"]}
    assert by_lemma["plante"]["translation_groups"] == [
        {
            "english_translation": "plant",
            "additional_translations": ["flora"],
        }
    ]
    assert by_lemma["ukendt"]["translation_groups"] == []


def _assign_category(conn, *, lexeme_id: int, meaning_id: int | None, label: str) -> None:
    normalized_label = label.lower()
    conn.execute(
        "INSERT OR IGNORE INTO wordbank_categories (label, normalized_label) VALUES (?, ?)",
        (label, normalized_label),
    )
    category_id = int(
        conn.execute(
            "SELECT id FROM wordbank_categories WHERE normalized_label = ?",
            (normalized_label,),
        ).fetchone()["id"]
    )
    conn.execute(
        """
        INSERT INTO wordbank_category_assignments (lexeme_id, meaning_id, category_id)
        VALUES (?, ?, ?)
        """,
        (lexeme_id, meaning_id, category_id),
    )

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.db.seed import seed_starter_data
from app.main import create_app


def _test_settings(db_path) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_trf-0.2.0",
    )


def test_db_init_creates_expected_tables(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"

    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        table_names = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {
        "schema_migrations",
        "lexemes",
        "lexeme_meanings",
        "surface_forms",
        "surface_form_cor_variants",
        "phrase_translations",
        "token_events",
        "typo_feedback",
        "ignored_tokens",
        "sentence_bank",
        "sentence_bank_tokens",
    }.issubset(table_names)


def test_backend_startup_recreates_db_after_delete(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    settings = _test_settings(db_path)

    assert not db_path.exists()
    app = create_app(settings, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200

    assert db_path.exists()


def test_seed_inserts_lexemes_and_is_repeatable(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    first = seed_starter_data(db_path)
    second = seed_starter_data(db_path)

    assert first["inserted_lexemes"] >= 3
    assert first["inserted_surface_forms"] >= 3
    assert second == {"inserted_lexemes": 0, "inserted_surface_forms": 0}

    with get_connection(db_path) as conn:
        lemmas = {
            row["lemma"] for row in conn.execute("SELECT lemma FROM lexemes").fetchall()
        }

    assert {"bog", "kan", "lide"}.issubset(lemmas)


def test_uniqueness_constraints_reject_duplicates(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO lexemes (lemma, source) VALUES (?, ?)", ("bog", "manual"))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO lexemes (lemma, source) VALUES (?, ?)",
                ("bog", "manual"),
            )

        lexeme_id = conn.execute(
            "SELECT id FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()["id"]

        conn.execute(
            "INSERT INTO surface_forms (lexeme_id, form, source) VALUES (?, ?, ?)",
            (lexeme_id, "bogen", "manual"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO surface_forms (lexeme_id, form, source) VALUES (?, ?, ?)",
                (lexeme_id, "bogen", "manual"),
            )
        surface_form_id = conn.execute(
            "SELECT id FROM surface_forms WHERE lexeme_id = ? AND form = ?",
            (lexeme_id, "bogen"),
        ).fetchone()["id"]

        conn.execute(
            "INSERT INTO surface_form_cor_variants (surface_form_id, cor_id) VALUES (?, ?)",
            (surface_form_id, "COR.123.110.01"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO surface_form_cor_variants (surface_form_id, cor_id) VALUES (?, ?)",
                (surface_form_id, "COR.123.110.01"),
            )

        conn.execute(
            "INSERT INTO ignored_tokens (token, scope) VALUES (?, ?)",
            ("plc", "global"),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO ignored_tokens (token, scope) VALUES (?, ?)",
                ("plc", "global"),
            )


def test_surface_form_cor_variants_has_expected_indexes(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'surface_form_cor_variants'"
            ).fetchall()
        }

    assert "idx_surface_form_cor_variants_surface_form_id" in indexes
    assert "idx_surface_form_cor_variants_cor_id" in indexes


def test_surface_form_cor_variants_has_expected_columns(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        columns = {
            row["name"]: row["type"]
            for row in conn.execute("PRAGMA table_info(surface_form_cor_variants)").fetchall()
        }

    assert columns == {
        "id": "INTEGER",
        "surface_form_id": "INTEGER",
        "cor_id": "TEXT",
        "created_at": "TEXT",
    }


def test_wordbank_related_words_table_has_expected_columns_and_indexes(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        columns = {
            row["name"]: row["type"]
            for row in conn.execute("PRAGMA table_info(wordbank_related_words)").fetchall()
        }
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'wordbank_related_words'"
            ).fetchall()
        }

    assert columns == {
        "id": "INTEGER",
        "owner_lexeme_id": "INTEGER",
        "relation_type": "TEXT",
        "sort_order": "INTEGER",
        "related_lemma": "TEXT",
        "english_translation": "TEXT",
        "pos_tag": "TEXT",
        "preferred_cor_id": "TEXT",
        "created_at": "TEXT",
        "updated_at": "TEXT",
    }
    assert "idx_wordbank_related_words_owner_lexeme_id" in indexes
    assert "idx_wordbank_related_words_owner_relation_order_unique" in indexes


def test_wordbank_additional_translations_table_has_expected_columns_and_indexes(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)

    with get_connection(db_path) as conn:
        columns = {
            row["name"]: row["type"]
            for row in conn.execute("PRAGMA table_info(wordbank_additional_translations)").fetchall()
        }
        indexes = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index' AND tbl_name = 'wordbank_additional_translations'"
            ).fetchall()
        }

    assert columns == {
        "id": "INTEGER",
        "lexeme_id": "INTEGER",
        "meaning_id": "INTEGER",
        "english_translation": "TEXT",
        "source": "TEXT",
        "created_at": "TEXT",
    }
    assert "idx_wordbank_additional_translations_scope" in indexes
    assert "idx_wordbank_additional_translations_scope_translation_unique" in indexes

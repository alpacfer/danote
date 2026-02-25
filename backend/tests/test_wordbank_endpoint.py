from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app


def _test_settings(db_path) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_tft-0.0.0",
        translation_enabled=False,
    )


def test_add_word_inserts_lemma_and_surface_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "inserted"
    assert payload["stored_lemma"] == "bog"
    assert payload["stored_surface_form"] == "bogen"
    assert payload["source"] == "manual"

    with get_connection(db_path) as conn:
        lexeme_row = conn.execute(
            "SELECT lemma, source FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT sf.form, sf.source
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE l.lemma = ? AND sf.form = ?
            """,
            ("bog", "bogen"),
        ).fetchone()

    assert lexeme_row is not None
    assert lexeme_row["source"] == "manual"
    assert surface_row is not None
    assert surface_row["source"] == "manual"


def test_add_word_duplicate_is_graceful(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        first = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "kat", "lemma_candidate": "kat"},
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "kat", "lemma_candidate": "kat"},
        )

    assert first.status_code == 200
    assert first.json()["status"] == "inserted"

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["status"] == "exists"
    assert "already" in second_payload["message"].lower()


def test_list_lemmas_returns_sorted_lemmas_with_variation_counts(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "huse", "lemma_candidate": "hus"})

        response = client.get("/api/wordbank/lemmas")

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == [
        {"lemma": "bog", "english_translation": None, "variation_count": 2},
        {"lemma": "hus", "english_translation": None, "variation_count": 1},
    ]


def test_get_lemma_details_returns_all_saved_variations(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        response = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lemma"] == "bog"
    assert payload["english_translation"] is None
    assert payload["surface_forms"] == ["bogen", "bogens"]


def test_get_lemma_details_returns_not_found_for_unknown_lemma(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.get("/api/wordbank/lemmas/missing")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_reset_database_clears_tables(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        reset_response = client.delete("/api/wordbank/database")

    assert reset_response.status_code == 200
    payload = reset_response.json()
    assert payload["status"] == "reset"
    assert "complete" in payload["message"].lower()

    with get_connection(db_path) as conn:
        lexeme_count = conn.execute("SELECT COUNT(*) AS count FROM lexemes").fetchone()
        surface_count = conn.execute("SELECT COUNT(*) AS count FROM surface_forms").fetchone()

    assert lexeme_count is not None
    assert surface_count is not None
    assert lexeme_count["count"] == 0
    assert surface_count["count"] == 0

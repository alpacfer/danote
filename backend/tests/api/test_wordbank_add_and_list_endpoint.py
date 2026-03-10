from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from tests.api.wordbank_test_support import build_test_settings, seed_cor_local_bog_senses


def test_add_word_inserts_lemma_and_surface_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

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
    assert payload["meaning"]["meaning_key"] == "bog"

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


def test_add_word_includes_verification_result_when_service_is_available(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "verified"
                message = "Storage payload is linguistically coherent."

            return Result()

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"]["status"] == "queued"
    assert payload["verification"]["provider"] == "gemini"
    assert payload["verification"]["reviewer_role"] == "Professional Danish Language Expert"
    assert payload["meaning"]["id"] is not None

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        verify_response = client.post(
            "/api/wordbank/lexemes/verify",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
                "meaning_id": payload["meaning"]["id"],
            },
        )

    assert verify_response.status_code == 200
    assert verify_response.json()["verification"]["status"] == "verified"


def test_add_word_duplicate_is_graceful(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        first = client.post("/api/wordbank/lexemes", json={"surface_token": "kat", "lemma_candidate": "kat"})
        second = client.post("/api/wordbank/lexemes", json={"surface_token": "kat", "lemma_candidate": "kat"})

    assert first.status_code == 200
    assert first.json()["status"] == "inserted"
    assert second.status_code == 200
    assert second.json()["status"] == "exists"
    assert "already" in second.json()["message"].lower()


def test_add_word_with_new_cor_id_for_existing_form_is_inserted(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        first = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )
        duplicate = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )

    assert first.status_code == 200
    assert first.json()["status"] == "inserted"
    assert second.status_code == 200
    assert second.json()["status"] == "inserted"
    assert first.json()["meaning"]["id"] != second.json()["meaning"]["id"]
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "exists"


def test_add_word_creates_non_verb_meaning_sections_from_gloss(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        first = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "moser", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.2"},
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert first.status_code == 200
    assert second.status_code == 200
    assert details.status_code == 200
    by_key = {section["meaning_key"]: section for section in details.json()["meaning_sections"]}
    assert set(by_key) == {"book", "swamp"}
    assert [item["form"] for item in by_key["book"]["surface_forms"]] == ["bogen"]
    assert [item["form"] for item in by_key["swamp"]["surface_forms"]] == ["moser"]


def test_add_word_saves_variation_under_existing_meaning_section(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bøger", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.2"},
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    section = details.json()["meaning_sections"][0]
    assert section["meaning_key"] == "book"
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bøger"]


def test_add_word_uses_gemini_to_route_variation_when_multiple_sections_exist(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, _payload) -> str | None:
            return None

        def translate_words_batch(self, payloads) -> list[str | None]:
            return [None for _ in payloads]

        def select_meaning_section(self, payload) -> int | None:
            for item in payload.meaning_candidates:
                if item.meaning_key == "swamp":
                    return item.id
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "moser", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.2"},
        )
        routed = client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        details = client.get("/api/wordbank/lemmas/bog")

    assert routed.status_code == 200
    by_key = {section["meaning_key"]: section for section in details.json()["meaning_sections"]}
    assert [item["form"] for item in by_key["swamp"]["surface_forms"]] == ["bogens", "moser"]


def test_add_word_creates_new_section_when_gemini_cannot_pick_existing_section(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, _payload) -> str | None:
            return None

        def translate_words_batch(self, payloads) -> list[str | None]:
            return [None for _ in payloads]

        def select_meaning_section(self, _payload) -> int | None:
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "moser", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.2"},
        )
        added = client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        details = client.get("/api/wordbank/lemmas/bog")

    assert added.status_code == 200
    assert added.json()["meaning"]["meaning_key"] == "bog"
    by_key = {section["meaning_key"]: section for section in details.json()["meaning_sections"]}
    assert [item["form"] for item in by_key["bog"]["surface_forms"]] == ["bogens"]


def test_list_lemmas_returns_sorted_lemmas_with_variation_counts(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "huse", "lemma_candidate": "hus"})
        response = client.get("/api/wordbank/lemmas")

    assert response.status_code == 200
    assert response.json()["items"] == [
        {"lemma": "bog", "display_lemma": "bog", "english_translation": None, "variation_count": 2},
        {"lemma": "hus", "display_lemma": "hus", "english_translation": None, "variation_count": 1},
    ]


def test_get_lemma_details_returns_all_saved_variations(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        response = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["lemma"] == "bog"
    assert payload["english_translation"] is None
    assert payload["is_sectioned"] is True
    assert payload["surface_forms"] == []
    section = payload["meaning_sections"][0]
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bogens"]
    assert all(item["has_pronunciation"] is False for item in section["surface_forms"])


def test_get_lemma_details_returns_not_found_for_unknown_lemma(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.get("/api/wordbank/lemmas/missing")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_reset_database_clears_tables(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        reset_response = client.delete("/api/wordbank/database")

    assert reset_response.status_code == 200
    assert reset_response.json()["status"] == "reset"

    with get_connection(db_path) as conn:
        lexeme_count = conn.execute("SELECT COUNT(*) AS count FROM lexemes").fetchone()
        surface_count = conn.execute("SELECT COUNT(*) AS count FROM surface_forms").fetchone()

    assert lexeme_count is not None
    assert surface_count is not None
    assert lexeme_count["count"] == 0
    assert surface_count["count"] == 0


def test_wordbank_endpoints_require_reset_for_legacy_non_verb_rows(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    with get_connection(db_path) as conn:
        conn.execute("INSERT INTO lexemes (lemma, source) VALUES (?, ?)", ("bog", "manual"))
        lexeme_row = conn.execute("SELECT id FROM lexemes WHERE lemma = ?", ("bog",)).fetchone()
        assert lexeme_row is not None
        conn.execute(
            "INSERT INTO surface_forms (lexeme_id, form, source) VALUES (?, ?, ?)",
            (int(lexeme_row["id"]), "bogen", "manual"),
        )

    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        list_response = client.get("/api/wordbank/lemmas")
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogens", "lemma_candidate": "bog"},
        )

    assert list_response.status_code == 503
    assert add_response.status_code == 503
    assert "reset the database" in list_response.json()["detail"].lower()
    assert "reset the database" in add_response.json()["detail"].lower()

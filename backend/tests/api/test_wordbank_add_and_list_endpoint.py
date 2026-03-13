from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from app.services.verification import WordVerificationAction
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
    verify_payload = verify_response.json()
    assert verify_payload["verification"]["status"] == "verified"
    assert verify_payload["verification"]["requested_at"] is not None
    assert verify_payload["verification"]["completed_at"] is not None

    with TestClient(app) as client:
        details_response = client.get("/api/wordbank/lemmas/bog")

    assert details_response.status_code == 200
    details_payload = details_response.json()
    assert details_payload["meaning_sections"][0]["verification"]["status"] == "verified"
    assert details_payload["meaning_sections"][0]["verification"]["completed_at"] is not None

    with get_connection(db_path) as conn:
        verification_row = conn.execute(
            """
            SELECT status, requested_at, completed_at
            FROM wordbank_verification_records
            """
        ).fetchone()

    assert verification_row is not None
    assert verification_row["status"] == "verified"
    assert verification_row["requested_at"] is not None
    assert verification_row["completed_at"] is not None


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


def test_get_lemma_details_non_sectioned_payload_omits_optional_surface_fields(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "lærer",
                "lemma_candidate": "lære",
                "search_seed": {
                    "lemma": "lære",
                    "surface": "lærer",
                    "cor_id": "COR.30686.203.01",
                    "cor_lemma_idx": 30686,
                    "meaning_key": "learn",
                    "gloss": "learn",
                    "english_translation": None,
                    "pos_tag": "VERB",
                    "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
                },
            },
        )
        response = client.get("/api/wordbank/lemmas/lære")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_sectioned"] is False
    assert payload["meaning_sections"] == []
    assert payload["surface_forms"] == [
        {
            "form": "lærer",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
            "has_pronunciation": False,
        }
    ]


def test_get_lemma_details_sectioned_payload_preserves_section_surface_fields(tmp_path, stub_nlp_adapter_factory) -> None:
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
        response = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_sectioned"] is True
    assert payload["surface_forms"] == []
    section_surface_form = payload["meaning_sections"][0]["surface_forms"][0]
    assert section_surface_form["form"] == "bogen"
    assert section_surface_form["lemma"] == "bog"
    assert section_surface_form["lemma_translation"] == "book"
    assert section_surface_form["gloss"] == "book"
    assert section_surface_form["gram_raw"] == "sb. fk. sg. best"


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


def test_add_word_search_seed_returns_saved_snapshot_and_stores_only_selected_surface(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "lærere",
                "lemma_candidate": "lærer",
                "search_seed": {
                    "lemma": "lærer",
                    "surface": "lærere",
                    "cor_id": "COR.49032.112.01",
                    "cor_lemma_idx": 49032,
                    "meaning_key": "teacher",
                    "gloss": "teacher",
                    "english_translation": "teacher",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Plur|Definite=Ind",
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["saved_snapshot"]["lemma"] == "lærer"
    assert payload["saved_snapshot"]["meaning_sections"][0]["english_translation"] == "teacher"
    assert [item["form"] for item in payload["saved_snapshot"]["meaning_sections"][0]["surface_forms"]] == ["lærere"]

    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT form
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE l.lemma = ?
            ORDER BY form ASC
            """,
            ("lærer",),
        ).fetchall()
    assert [str(row["form"]) for row in rows] == ["lærere"]


def test_add_word_search_seed_routes_variation_to_target_meaning(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        first = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bogen",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bogen",
                    "cor_id": "COR.BOG.BOOK.1",
                    "cor_lemma_idx": 123,
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Def",
                },
            },
        )
        first_meaning_id = first.json()["meaning"]["id"]
        second = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bøger",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bøger",
                    "cor_id": "COR.BOG.BOOK.2",
                    "cor_lemma_idx": 123,
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Plur|Definite=Ind",
                    "target_meaning_id": first_meaning_id,
                },
            },
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert second.status_code == 200
    section = details.json()["meaning_sections"][0]
    assert section["id"] == first_meaning_id
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bøger"]


def test_add_word_search_seed_keeps_partial_translation_data(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "lærer",
                "lemma_candidate": "lære",
                "search_seed": {
                    "lemma": "lære",
                    "surface": "lærer",
                    "cor_id": "COR.30686.203.01",
                    "cor_lemma_idx": 30686,
                    "meaning_key": "learn",
                    "gloss": "learn",
                    "english_translation": None,
                    "pos_tag": "VERB",
                    "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
                },
            },
        )
        details = client.get("/api/wordbank/lemmas/lære")

    assert response.status_code == 200
    assert response.json()["saved_snapshot"]["english_translation"] is None
    assert details.json()["english_translation"] is None
    assert [item["form"] for item in details.json()["surface_forms"]] == ["lærer"]


def test_add_word_search_seed_enqueues_and_runs_background_jobs(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def __init__(self) -> None:
            self.calls = 0

        def verify_word_entry(self, _payload):
            self.calls += 1

            class Result:
                verdict = "verified"
                message = "Looks good."

            return Result()

    class StubTTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def __init__(self) -> None:
            self.calls = 0

        def synthesize(self, text: str):
            from app.services.tts import PronunciationAudio

            self.calls += 1
            return PronunciationAudio(audio_bytes=f"{text}-wav".encode(), mime_type="audio/wav")

    verification_service = StubVerificationService()
    tts_service = StubTTSService()

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", verification_service)
        set_service_field(client.app, "tts_service", tts_service)
        response = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bogen",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bogen",
                    "cor_id": "COR.BOG.BOOK.1",
                    "cor_lemma_idx": 123,
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Def",
                },
            },
        )

        deadline = time.time() + 5
        while time.time() < deadline:
            with get_connection(db_path) as conn:
                jobs = conn.execute(
                    "SELECT status FROM wordbank_background_jobs ORDER BY id ASC"
                ).fetchall()
                audio_row = conn.execute(
                    """
                    SELECT pronunciation_audio
                    FROM surface_forms sf
                    JOIN lexemes l ON l.id = sf.lexeme_id
                    WHERE l.lemma = ? AND sf.form = ?
                    """,
                    ("bog", "bogen"),
                ).fetchone()
            if jobs and all(str(job["status"]) == "completed" for job in jobs) and audio_row and audio_row["pronunciation_audio"]:
                break
            time.sleep(0.05)

    assert response.status_code == 200
    assert verification_service.calls >= 1
    assert tts_service.calls >= 1

    with get_connection(db_path) as conn:
        verification_row = conn.execute(
            """
            SELECT status, completed_at
            FROM wordbank_verification_records
            """
        ).fetchone()

    assert verification_row is not None
    assert verification_row["status"] == "verified"
    assert verification_row["completed_at"] is not None

    with TestClient(app) as client:
        details = client.get("/api/wordbank/lemmas/bog")

    assert details.status_code == 200
    assert details.json()["meaning_sections"][0]["verification"]["status"] == "verified"


def test_apply_verification_changes_prunes_persisted_suggestions(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "flagged"
                message = "incorrect"
                problem = "Translation is wrong."
                change_to_implement = "Set translation to book."
                suggested_actions = (
                    WordVerificationAction(
                        action_type="fix_translation",
                        english_translation="book",
                        reason="Use the singular noun translation.",
                    ),
                )

            return Result()

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        added = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )
        added_payload = added.json()
        verify = client.post(
            "/api/wordbank/lexemes/verify",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
                "meaning_id": added_payload["meaning"]["id"],
            },
        )

        assert verify.status_code == 200
        details_before = client.get("/api/wordbank/lemmas/bog")
        assert details_before.status_code == 200
        action = details_before.json()["meaning_sections"][0]["verification"]["suggested_actions"][0]

        apply_response = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
                "meaning_id": added_payload["meaning"]["id"],
                "provider": "gemini",
                "action": action,
            },
        )

        details_after = client.get("/api/wordbank/lemmas/bog")

    assert apply_response.status_code == 200
    assert apply_response.json()["status"] == "applied"
    assert details_after.status_code == 200
    assert details_after.json()["meaning_sections"][0].get("verification") is None

    with get_connection(db_path) as conn:
        remaining_rows = conn.execute(
            "SELECT COUNT(*) AS count FROM wordbank_verification_records"
        ).fetchone()

    assert remaining_rows is not None
    assert int(remaining_rows["count"]) == 0

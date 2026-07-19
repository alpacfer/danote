from __future__ import annotations

import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from tests.api.wordbank_test_support import (
    build_test_settings,
    seed_cor_local_bog_senses,
    seed_cor_local_db,
    seed_cor_local_word_page_gloss_cases,
)


def _seed_complete_bog_paradigm_cor_local(db_path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE cor_entries (
                cor_id TEXT PRIMARY KEY,
                lemma TEXT NOT NULL,
                gloss TEXT,
                gram TEXT NOT NULL,
                form TEXT NOT NULL,
                norm TEXT NOT NULL,
                lemma_idx INTEGER NOT NULL,
                gram_code INTEGER NOT NULL,
                variation INTEGER NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX idx_cor_form ON cor_entries(form)")
        conn.execute("CREATE INDEX idx_cor_form_lower ON cor_entries(lower(form))")
        conn.execute("CREATE INDEX idx_cor_lemma_idx ON cor_entries(lemma_idx)")
        conn.execute("CREATE INDEX idx_cor_lemma_gram ON cor_entries(lemma, gram)")
        conn.executemany(
            """
            INSERT INTO cor_entries (
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ("COR.BOG.BOOK.LEM", "bog", "book", "sb.fk.sg.ubest", "bog", "N", 123, 110, 1),
                ("COR.BOG.BOOK.DEF", "bog", "book", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),
                ("COR.BOG.BOOK.PL", "bog", "book", "sb.fk.pl.ubest", "bøger", "N", 123, 112, 1),
                ("COR.BOG.BOOK.PLDEF", "bog", "book", "sb.fk.pl.best", "bøgerne", "N", 123, 113, 1),
                ("COR.BOG.SWAMP.LEM", "bog", "swamp", "sb.fk.sg.ubest", "bog", "N", 124, 210, 1),
                ("COR.BOG.SWAMP.DEF", "bog", "swamp", "sb.fk.sg.best", "bogen", "N", 124, 211, 1),
                ("COR.BOG.SWAMP.PL", "bog", "swamp", "sb.fk.pl.ubest", "moser", "N", 124, 212, 1),
                ("COR.BOG.SWAMP.PLDEF", "bog", "swamp", "sb.fk.pl.best", "moserne", "N", 124, 213, 1),
            ),
        )


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
    assert payload["queued_pronunciation_forms"] == []

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
                message = "OK"

            return Result()

        def classify_word_categories(self, _payload):
            class Result:
                categories = ("Food", "Furniture")

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
    assert verify_payload["applied_categories"] == ["Food", "Furniture"]
    assert verify_payload["verification"]["requested_at"] is not None
    assert verify_payload["verification"]["completed_at"] is not None

    details_payload = None
    deadline = time.time() + 5
    while time.time() < deadline:
        with TestClient(app) as client:
            details_response = client.get("/api/wordbank/lemmas/bog")
        assert details_response.status_code == 200
        candidate = details_response.json()
        meaning_verification = candidate["meaning_sections"][0]["verification"]
        variation_row = next(
            (item for item in candidate["meaning_sections"][0]["surface_forms"] if item["form"] == "bogen"),
            None,
        )
        surface_verification = variation_row.get("verification") if variation_row is not None else None
        if (
            candidate["meaning_sections"][0]["categories"] == ["Food", "Furniture"]
            and meaning_verification is not None
            and meaning_verification["status"] in {"queued", "verified"}
            and surface_verification is not None
            and surface_verification["status"] == "verified"
        ):
            details_payload = candidate
            break
        time.sleep(0.05)

    assert details_payload is not None
    assert details_payload["meaning_sections"][0]["categories"] == ["Food", "Furniture"]
    assert details_payload["meaning_sections"][0]["verification"]["status"] in {"queued", "verified"}
    verified_surface = next(
        item for item in details_payload["meaning_sections"][0]["surface_forms"] if item["form"] == "bogen"
    )
    assert verified_surface["verification"]["status"] == "verified"
    assert verified_surface["verification"]["completed_at"] is not None

    verification_rows = None
    deadline = time.time() + 5
    while time.time() < deadline:
        with get_connection(db_path) as conn:
            candidate_rows = conn.execute(
                """
                SELECT status, stored_surface_form, requested_at, completed_at
                FROM wordbank_verification_records
                ORDER BY id ASC
                """
            ).fetchall()
        if len(candidate_rows) == 2 and any(
            row["stored_surface_form"] == "bogen" and row["status"] == "verified"
            for row in candidate_rows
        ):
            verification_rows = candidate_rows
            break
        time.sleep(0.05)

    assert verification_rows is not None
    assert len(verification_rows) == 2
    meaning_row = next(row for row in verification_rows if row["stored_surface_form"] is None)
    surface_row = next(row for row in verification_rows if row["stored_surface_form"] == "bogen")
    assert meaning_row["status"] in {"queued", "verified"}
    assert meaning_row["requested_at"] is not None
    assert surface_row["status"] == "verified"
    assert surface_row["requested_at"] is not None
    assert surface_row["completed_at"] is not None


def test_rethink_categories_updates_meaning_categories(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "verified"
                message = "OK"

            return Result()

        def classify_word_categories(self, _payload):
            class Result:
                categories = ("Food", "Reading Material", "Education", "Culture")

            return Result()

    with TestClient(app) as client:
        added = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )
        added_payload = added.json()

    assert added.status_code == 200
    assert added_payload["meaning"]["id"] is not None

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        rethink_response = client.post(
            "/api/wordbank/lexemes/rethink-categories",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": None,
                "meaning_id": added_payload["meaning"]["id"],
            },
        )

    assert rethink_response.status_code == 200
    rethink_payload = rethink_response.json()
    assert rethink_payload["status"] == "updated"
    assert rethink_payload["applied_categories"] == ["Culture", "Education", "Food", "Reading Material"]

    with TestClient(app) as client:
        details = client.get("/api/wordbank/lemmas/bog")

    assert details.status_code == 200
    assert details.json()["meaning_sections"][0]["categories"] == ["Culture", "Education", "Food", "Reading Material"]


def test_find_alternative_translations_updates_meaning_translation_and_additional_translations(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def find_alternative_translations(self, payload):
            if payload.lemma == "plads" and payload.gloss == "space" and payload.current_translation == "seat":
                from app.services.gemini_translation import AlternativeTranslationsResult

                return AlternativeTranslationsResult(
                    primary_translation="place",
                    alternative_translations=["spot", "seat"],
                )
            raise AssertionError("Unexpected alternative translations payload.")

    with TestClient(app) as client:
        added = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "plads",
                "lemma_candidate": "plads",
                "search_seed": {
                    "lemma": "plads",
                    "surface": "plads",
                    "meaning_key": "space",
                    "gloss": "space",
                    "english_translation": "seat",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Ind",
                },
            },
        )
        meaning_id = added.json()["meaning"]["id"]

    with TestClient(app) as client:
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        response = client.post(
            "/api/wordbank/lexemes/find-alternative-translations",
            json={
                "stored_lemma": "plads",
                "meaning_id": meaning_id,
            },
        )
        details = client.get("/api/wordbank/lemmas/plads")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "updated"
    assert payload["primary_translation"] == "place"
    assert payload["added_additional_translations"] == ["spot", "seat"]
    assert details.status_code == 200
    assert details.json()["meaning_sections"][0]["english_translation"] == "place"
    assert details.json()["meaning_sections"][0]["additional_translations"] == ["spot", "seat"]


@pytest.mark.parametrize("use_root_scope", [False, True])
def test_complete_variations_endpoint_adds_missing_forms_and_enqueues_jobs(
    tmp_path,
    stub_nlp_adapter_factory,
    use_root_scope: bool,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_complete_bog_paradigm_cor_local(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "verified"
                message = "Looks good."

            return Result()

    class StubTTSService:
        provider = "gemini_tts"
        model = "gemini-2.5-flash-preview-tts"

        def synthesize(self, text: str):
            from app.services.tts import PronunciationAudio

            return PronunciationAudio(audio_bytes=f"{text}-wav".encode(), mime_type="audio/wav")

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def complete_non_cor_meaning_variations(self, payload):
            from app.services.gemini_translation import (
                NonCORVariationCandidate,
                NonCORVariationGenerationResult,
            )
            return NonCORVariationGenerationResult(
                forms=[
                    NonCORVariationCandidate(
                        form="bogen",
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Sing|Definite=Def",
                    ),
                    NonCORVariationCandidate(
                        form="bøgerne",
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Def",
                    ),
                ]
            )

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        set_service_field(client.app, "tts_service", StubTTSService())
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        added = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bøger",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bøger",
                    "cor_id": "COR.BOG.BOOK.PL",
                    "cor_lemma_idx": 123,
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Plur|Definite=Ind",
                },
            },
        )
        assert added.status_code == 200
        meaning_id = added.json()["meaning"]["id"]
        meaning_verify = client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": None, "meaning_id": meaning_id},
        )
        surface_verify = client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": "bøger", "meaning_id": meaning_id},
        )
        assert meaning_verify.status_code == 200
        assert surface_verify.status_code == 200
        response = client.post(
            "/api/wordbank/lexemes/complete-variations",
            json={
                "stored_lemma": "bog",
                "meaning_id": None if use_root_scope else meaning_id,
            },
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "updated"
    assert payload["meaning_id"] == meaning_id
    assert payload["added_surface_forms"] == ["bogen", "bøgerne"]
    assert payload["queued_pronunciation_forms"] == ["bog", "bogen", "bøgerne"]
    assert [item["form"] for item in details.json()["meaning_sections"][0]["surface_forms"]] == ["bogen", "bøger", "bøgerne"]

    with get_connection(db_path) as conn:
        pronunciation_jobs = conn.execute(
            """
            SELECT dedupe_key, payload_json
            FROM wordbank_background_jobs
            WHERE job_type = 'generate_pronunciation'
            ORDER BY dedupe_key ASC
            """
        ).fetchall()
    assert [str(row["dedupe_key"]) for row in pronunciation_jobs] == ["generate_pronunciation::bog"]
    assert json.loads(str(pronunciation_jobs[0]["payload_json"])) == {
        "force": False,
        "requested_forms": ["bog", "bøger", "bogen", "bøgerne"],
        "stored_lemma": "bog",
    }


def test_complete_variations_endpoint_scopes_to_selected_homograph_meaning(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_complete_bog_paradigm_cor_local(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "verified"
                message = "Looks good."

            return Result()

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def complete_non_cor_meaning_variations(self, payload):
            from app.services.gemini_translation import (
                NonCORVariationCandidate,
                NonCORVariationGenerationResult,
            )
            return NonCORVariationGenerationResult(
                forms=[
                    NonCORVariationCandidate(
                        form="bøger",
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Ind",
                    ),
                    NonCORVariationCandidate(
                        form="bøgerne",
                        pos_tag="NOUN",
                        morphology="Gender=Com|Number=Plur|Definite=Def",
                    ),
                ]
            )

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        first = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bogen",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bogen",
                    "cor_id": "COR.BOG.BOOK.DEF",
                    "cor_lemma_idx": 123,
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Def",
                },
            },
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bogen",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bogen",
                    "cor_id": "COR.BOG.SWAMP.DEF",
                    "cor_lemma_idx": 124,
                    "meaning_key": "swamp",
                    "gloss": "swamp",
                    "english_translation": "swamp",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Def",
                },
            },
        )
        assert first.status_code == 200
        assert second.status_code == 200
        meaning_id = first.json()["meaning"]["id"]
        meaning_verify = client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": None, "meaning_id": meaning_id},
        )
        surface_verify = client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": "bogen", "meaning_id": meaning_id},
        )
        assert meaning_verify.status_code == 200
        assert surface_verify.status_code == 200
        response = client.post(
            "/api/wordbank/lexemes/complete-variations",
            json={
                "stored_lemma": "bog",
                "meaning_id": meaning_id,
            },
        )
        ambiguous_root = client.post(
            "/api/wordbank/lexemes/complete-variations",
            json={
                "stored_lemma": "bog",
                "meaning_id": None,
            },
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert response.status_code == 200
    assert ambiguous_root.status_code == 400
    assert "does not have exactly one saved meaning" in ambiguous_root.json()["detail"]
    sections = details.json()["meaning_sections"]
    assert [item["form"] for item in sections[0]["surface_forms"]] == ["bogen", "bøger", "bøgerne"]
    assert [item["form"] for item in sections[1]["surface_forms"]] == ["bogen"]


def test_complete_variations_endpoint_skips_without_cor_identity_and_404s_for_invalid_meaning(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_complete_bog_paradigm_cor_local(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubVerificationService:
        provider = "gemini"
        reviewer_role = "Professional Danish Language Expert"

        def verify_word_entry(self, _payload):
            class Result:
                verdict = "verified"
                message = "Looks good."

            return Result()

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def complete_non_cor_meaning_variations(self, payload):
            raise RuntimeError("missing_cor_identity")

    with TestClient(app) as client:
        set_service_field(client.app, "word_verification_service", StubVerificationService())
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        manual = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bogen",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bogen",
                    "cor_id": "COR.BOG.BOOK.DEF",
                    "meaning_key": "book",
                    "gloss": "book",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Def",
                },
            },
        )
        meaning_id = manual.json()["meaning"]["id"]
        client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": None, "meaning_id": meaning_id},
        )
        client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": "bogen", "meaning_id": meaning_id},
        )
        skipped = client.post(
            "/api/wordbank/lexemes/complete-variations",
            json={
                "stored_lemma": "bog",
                "meaning_id": meaning_id,
            },
        )
        missing = client.post(
            "/api/wordbank/lexemes/complete-variations",
            json={
                "stored_lemma": "bog",
                "meaning_id": 999,
            },
        )

    assert skipped.status_code == 200
    assert skipped.json()["status"] == "skipped"
    assert "COR identity" in skipped.json()["message"]
    assert missing.status_code == 404


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
    items = response.json()["items"]
    assert all(item["created_at"] for item in items)
    assert all(item["last_enriched_at"] >= item["created_at"] for item in items)
    assert [
        {
            key: value
            for key, value in item.items()
            if key not in {"created_at", "last_enriched_at"}
        }
        for item in items
    ] == [
        {
            "lemma": "bog",
            "display_lemma": "bog",
            "english_translation": None,
            "pos_tags": [],
            "categories": [],
            "variation_count": 2,
            "translation_groups": [],
        },
        {
            "lemma": "hus",
            "display_lemma": "hus",
            "english_translation": None,
            "pos_tags": [],
            "categories": [],
            "variation_count": 1,
            "translation_groups": [],
        },
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
    assert payload["surface_forms"] == [
        {
            "form": "bog",
            "has_pronunciation": False,
        }
    ]
    section = payload["meaning_sections"][0]
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bogens"]
    assert all(item["has_pronunciation"] is False for item in section["surface_forms"])


def test_get_lemma_details_sectioned_verb_payload_includes_cor_grammar_when_available(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

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
                    "english_translation": "learn",
                    "pos_tag": "VERB",
                    "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
                },
            },
        )
        response = client.get("/api/wordbank/lemmas/lære")

    assert response.status_code == 200
    payload = response.json()
    assert payload["is_sectioned"] is True
    assert payload["pos_tag"] == "VERB"
    assert payload["morphology"] == "VerbForm=Inf|Voice=Act"
    assert payload["surface_forms"] == []
    assert len(payload["meaning_sections"]) == 1
    assert payload["meaning_sections"][0]["meaning_key"] == "learn"
    assert payload["meaning_sections"][0]["pos_tag"] == "VERB"
    assert payload["meaning_sections"][0]["morphology"] == "VerbForm=Inf|Voice=Act"
    assert payload["meaning_sections"][0]["surface_forms"] == [
        {
            "form": "lærer",
            "pos_tag": "VERB",
            "morphology": "Tense=Pres|VerbForm=Fin|Voice=Act",
            "lemma": "lære",
            "lemma_translation": "learn",
            "gloss": "learn",
            "gram_raw": "vb. præs. akt",
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
    assert len(payload["surface_forms"]) == 1
    assert payload["surface_forms"][0]["form"] == "bog"
    assert payload["surface_forms"][0]["pos_tag"] == "NOUN"
    assert payload["surface_forms"][0]["has_pronunciation"] is False
    assert "gram_raw" in payload["surface_forms"][0]
    section_surface_form = next(
        item for item in payload["meaning_sections"][0]["surface_forms"] if item["form"] == "bogen"
    )
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


def test_contract_add_word_search_seed_returns_saved_snapshot_and_stores_only_selected_surface(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

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
    assert payload["saved_snapshot"]["pos_tag"] == "NOUN"
    assert payload["saved_snapshot"]["morphology"] == "Gender=Com|Number=Sing|Definite=Ind"
    assert payload["saved_snapshot"]["meaning_sections"][0]["english_translation"] == "teacher"
    assert payload["saved_snapshot"]["meaning_sections"][0]["morphology"] == "Gender=Com|Number=Sing|Definite=Ind"
    assert [item["form"] for item in payload["saved_snapshot"]["meaning_sections"][0]["surface_forms"]] == ["lærere"]
    assert payload["saved_snapshot"]["meaning_sections"][0]["surface_forms"][0]["morphology"] == "Gender=Com|Number=Plur|Definite=Ind"

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


def test_contract_search_seed_saved_snapshot_and_word_page_include_gloss_translation_for_homographs(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_word_page_gloss_cases(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return {
                "til læsning": "for reading",
                "frugt fra et bøgetræ": "fruit from a beech tree",
            }.get(text)

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        first = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bog",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bog",
                    "cor_id": "COR.BOG.READING.LEM",
                    "cor_lemma_idx": 123,
                    "meaning_key": "for-reading",
                    "gloss": "til læsning",
                    "english_translation": "book",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Ind",
                },
            },
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "bog",
                "lemma_candidate": "bog",
                "search_seed": {
                    "lemma": "bog",
                    "surface": "bog",
                    "cor_id": "COR.BOG.BEECHMAST.LEM",
                    "cor_lemma_idx": 124,
                    "meaning_key": "beechmast",
                    "gloss": "frugt fra et bøgetræ",
                    "english_translation": "beechmast",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Neut|Number=Sing|Definite=Ind",
                },
            },
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert first.status_code == 200
    assert second.status_code == 200
    assert details.status_code == 200
    first_snapshot = first.json()["saved_snapshot"]
    assert first_snapshot["meaning_sections"][0]["english_translation"] == "book"
    assert first_snapshot["meaning_sections"][0]["gloss_translation"] == "for reading"
    sections = details.json()["meaning_sections"]
    assert [section["english_translation"] for section in sections] == ["book", "beechmast"]
    assert [section["gloss_translation"] for section in sections] == [
        "for reading",
        "fruit from a beech tree",
    ]


def test_contract_word_page_details_keep_translation_and_translated_gloss_for_mor_homographs(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_word_page_gloss_cases(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return {
                "en mor": "a mother",
                "person": "person",
                "jordlag": "soil layer",
            }.get(text)

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        first = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Mor", "lemma_candidate": "mor", "cor_id": "COR.MOR.PERSON.LEM"},
        )
        second = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Mor", "lemma_candidate": "mor", "cor_id": "COR.MOR.SOIL.LEM"},
        )
        details = client.get("/api/wordbank/lemmas/mor")

    assert first.status_code == 200
    assert second.status_code == 200
    assert details.status_code == 200
    payload = details.json()
    assert payload["english_translation"] is None
    assert [section["english_translation"] for section in payload["meaning_sections"]] == ["mother", "mother"]
    assert [section["gloss_translation"] for section in payload["meaning_sections"]] == ["person", "soil layer"]


def test_add_word_search_seed_repeat_save_repairs_surface_derived_metadata(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)

    initial_app = create_app(
        build_test_settings(db_path, cor_local_db_path=tmp_path / "missing-cor.sqlite"),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )
    with TestClient(initial_app) as client:
        initial = client.post(
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
        initial_details = client.get("/api/wordbank/lemmas/lærer")

    repaired_app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )
    with TestClient(repaired_app) as client:
        repeated = client.post(
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
        repaired_details = client.get("/api/wordbank/lemmas/lærer")

    assert initial.status_code == 200
    assert repeated.status_code == 200
    assert initial_details.json()["meaning_sections"][0]["morphology"] == "Gender=Com|Number=Plur|Definite=Ind"
    assert repaired_details.json()["meaning_sections"][0]["morphology"] == "Gender=Com|Number=Sing|Definite=Ind"
    assert repaired_details.json()["meaning_sections"][0]["surface_forms"][0]["morphology"] == "Gender=Com|Number=Plur|Definite=Ind"


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


def test_add_word_search_seed_allows_missing_translation_and_saves_blank(
    tmp_path, stub_nlp_adapter_factory
) -> None:
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
    assert response.json()["meaning"]["english_translation"] is None
    assert details.status_code == 200
    assert details.json()["meaning_sections"][0].get("english_translation") is None


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


def test_apply_verification_changes_rejects_surface_scoped_fix_translation(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        added = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )
        added_payload = added.json()

        apply_response = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
                "meaning_id": added_payload["meaning"]["id"],
                "provider": "gemini",
                "action": {
                    "action_type": "fix_translation",
                    "english_translation": "book",
                },
            },
        )

    assert apply_response.status_code == 400
    assert "surface-form verification targets" in apply_response.json()["detail"]


def test_verification_change_history_endpoints_list_and_revert(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        added = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )
        assert added.status_code == 200
        meaning_id = added.json()["meaning"]["id"]

        applied = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": None,
                "meaning_id": meaning_id,
                "provider": "gemini",
                "action": {
                    "action_type": "fix_translation",
                    "english_translation": "book",
                },
            },
        )
        assert applied.status_code == 200

        changes = client.get(
            "/api/wordbank/lexemes/verification-changes",
            params={"stored_lemma": "bog"},
        )

        assert changes.status_code == 200
        payload = changes.json()
        assert len(payload["items"]) == 1
        assert payload["items"][0]["action_type"] == "fix_translation"
        assert payload["items"][0]["stored_lemma"] == "bog"
        change_id = payload["items"][0]["id"]

        reverted = client.post(
            "/api/wordbank/lexemes/revert-verification-change",
            json={"change_id": change_id, "stored_lemma": "bog"},
        )

    assert reverted.status_code == 200
    assert reverted.json()["status"] == "reverted"

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            "SELECT english_translation FROM lexeme_meanings WHERE id = ?",
            (meaning_id,),
        ).fetchone()
        change_row = conn.execute(
            "SELECT reverted_at FROM verification_change_log WHERE id = ?",
            (change_id,),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["english_translation"] is None
    assert change_row is not None
    assert change_row["reverted_at"] is not None

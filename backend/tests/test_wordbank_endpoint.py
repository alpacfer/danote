from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.core.config import Settings
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from app.services.tts import PronunciationAudio


def _test_settings(db_path, *, cor_local_db_path=None) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_trf-0.2.0",
        translation_enabled=False,
        cor_local_db_path=cor_local_db_path or (db_path.parent / "cor.sqlite"),
    )


def _seed_cor_local_db(db_path) -> None:
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
                ("COR.49032.110.01", "lærer", "teacher", "sb.fk.sg.ubest", "lærer", "N", 49032, 110, 1),
                ("COR.49032.112.01", "lærer", "teacher", "sb.fk.pl.ubest", "lærere", "N", 49032, 112, 1),
                ("COR.30686.203.01", "lære", "learn", "vb.præs.akt", "lærer", "N", 30686, 203, 1),
            ),
        )


def _seed_cor_local_bog_senses(db_path) -> None:
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
                ("COR.BOG.BOOK.1", "bog", "book", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),
                ("COR.BOG.BOOK.2", "bog", "book", "sb.fk.pl.ubest", "bøger", "N", 123, 112, 1),
                ("COR.BOG.SWAMP.1", "bog", "swamp", "sb.fk.sg.best", "bogen", "N", 124, 211, 1),
                ("COR.BOG.SWAMP.2", "bog", "swamp", "sb.fk.pl.ubest", "moser", "N", 124, 212, 1),
            ),
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
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

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


def test_add_word_with_new_cor_id_for_existing_form_is_inserted(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
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
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
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
    payload = details.json()
    assert payload["is_sectioned"] is True
    assert len(payload["meaning_sections"]) == 2
    by_key = {section["meaning_key"]: section for section in payload["meaning_sections"]}
    assert set(by_key) == {"book", "swamp"}
    assert [item["form"] for item in by_key["book"]["surface_forms"]] == ["bogen"]
    assert [item["form"] for item in by_key["swamp"]["surface_forms"]] == ["moser"]


def test_add_word_saves_variation_under_existing_meaning_section(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
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
    payload = details.json()
    assert payload["is_sectioned"] is True
    assert len(payload["meaning_sections"]) == 1
    section = payload["meaning_sections"][0]
    assert section["meaning_key"] == "book"
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bøger"]


def test_add_word_uses_gemini_to_route_variation_when_multiple_sections_exist(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
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
        routed = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogens", "lemma_candidate": "bog"},
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert routed.status_code == 200
    payload = details.json()
    by_key = {section["meaning_key"]: section for section in payload["meaning_sections"]}
    assert "swamp" in by_key
    assert [item["form"] for item in by_key["swamp"]["surface_forms"]] == ["bogens", "moser"]


def test_add_word_creates_new_section_when_gemini_cannot_pick_existing_section(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
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
        added = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogens", "lemma_candidate": "bog"},
        )
        details = client.get("/api/wordbank/lemmas/bog")

    assert added.status_code == 200
    assert added.json()["meaning"]["meaning_key"] == "bog"
    payload = details.json()
    by_key = {section["meaning_key"]: section for section in payload["meaning_sections"]}
    assert "bog" in by_key
    assert [item["form"] for item in by_key["bog"]["surface_forms"]] == ["bogens"]


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
        {"lemma": "bog", "display_lemma": "bog", "english_translation": None, "variation_count": 2},
        {"lemma": "hus", "display_lemma": "hus", "english_translation": None, "variation_count": 1},
    ]


def test_wordbank_endpoints_require_reset_for_legacy_non_verb_rows(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT INTO lexemes (lemma, source) VALUES (?, ?)",
            ("bog", "manual"),
        )
        lexeme_row = conn.execute(
            "SELECT id FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()
        assert lexeme_row is not None
        conn.execute(
            "INSERT INTO surface_forms (lexeme_id, form, source) VALUES (?, ?, ?)",
            (int(lexeme_row["id"]), "bogen", "manual"),
        )

    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        list_response = client.get("/api/wordbank/lemmas")
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogens", "lemma_candidate": "bog"},
        )

    assert list_response.status_code == 503
    assert "reset the database" in list_response.json()["detail"].lower()
    assert add_response.status_code == 503
    assert "reset the database" in add_response.json()["detail"].lower()


def test_search_lemmas_returns_variation_matches(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        response = client.get("/api/wordbank/search", params={"query": "gens"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["lemma"] == "bog"
    assert item["display_lemma"] == "bog"
    assert item["meaning_id"] is not None
    assert item["meaning_key"] == "bog"
    assert item["gloss"] is None
    assert item["cor_lemma_idx"] is None
    assert item["english_translation"] is None
    assert item["variation_count"] == 2
    assert item["match_surface"] == "bogens"
    assert item["query_cor_ids"] == []
    assert item["pos_tag"] is None
    assert item["morphology"] is None


def test_search_lemmas_prefers_matched_surface_metadata(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "ulykker",
                "lemma_candidate": "ulykke",
                "pos_tag": "NOUN",
                "morphology": "Gender=Com|Number=Plur|Definite=Ind",
            },
        )
        response = client.get("/api/wordbank/search", params={"query": "ulykker"})

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) == 1
    item = payload["items"][0]
    assert item["lemma"] == "ulykke"
    assert item["display_lemma"] == "ulykke"
    assert item["meaning_id"] is not None
    assert item["meaning_key"] == "ulykke"
    assert item["gloss"] is None
    assert item["cor_lemma_idx"] is None
    assert item["english_translation"] is None
    assert item["variation_count"] == 2
    assert item["match_surface"] == "ulykker"
    assert item["query_cor_ids"] == []
    assert item["pos_tag"] == "NOUN"
    assert item["morphology"] == "Gender=Com|Number=Plur|Definite=Ind"


def test_search_lemmas_returns_query_cor_ids_for_exact_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )
        response = client.get("/api/wordbank/search", params={"query": "bogen"})

    assert response.status_code == 200
    payload = response.json()
    assert [(item["meaning_key"], item["query_cor_ids"], item["cor_lemma_idx"]) for item in payload["items"]] == [
        ("book", ["COR.BOG.BOOK.1"], 123),
        ("swamp", ["COR.BOG.SWAMP.1"], 124),
    ]
    assert [item["match_surface"] for item in payload["items"]] == ["bogen", "bogen"]


def test_search_lemmas_returns_two_rows_for_exact_homograph_lemma(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_bog_senses(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )
        response = client.get("/api/wordbank/search", params={"query": "bog"})

    assert response.status_code == 200
    payload = response.json()
    assert [(item["meaning_key"], item["match_surface"], item["english_translation"]) for item in payload["items"]] == [
        ("book", "bog", "book"),
        ("swamp", "bog", "swamp"),
    ]


def test_search_cor_form_returns_grouped_variants(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_db(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "LÆRER", "include_translations": "false"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["form"] == "lærer"
    assert len(payload["groups"]) == 2
    by_key = {(item["lemma"], item["pos_tag"]): item for item in payload["groups"]}
    noun_group = by_key[("lærer", "NOUN")]
    assert noun_group["gloss"] == "teacher"
    assert [item["cor_id"] for item in noun_group["variants"]] == ["COR.49032.110.01"]
    verb_group = by_key[("lære", "VERB")]
    assert verb_group["gloss"] == "learn"


def test_search_cor_lemma_returns_paradigm_forms(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_db(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-lemma/49032", params={"limit": 1000})

    assert response.status_code == 200
    payload = response.json()
    assert payload["lemma_idx"] == 49032
    assert [item["form"] for item in payload["variants"]] == ["lærer", "lærere"]


def test_search_cor_form_works_when_nlp_is_unavailable(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_db(cor_db_path)

    def failing_nlp_factory(_settings):
        raise RuntimeError("NLP startup failed")

    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=failing_nlp_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "lærer", "include_translations": "false"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["form"] == "lærer"
    assert len(payload["groups"]) == 2


def test_search_cor_form_returns_azure_error_when_translations_requested_without_service(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    _seed_cor_local_db(cor_db_path)
    app = create_app(
        _test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "lærer"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Azure translation is unavailable."


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
    assert payload["is_sectioned"] is True
    assert payload["surface_forms"] == []
    assert len(payload["meaning_sections"]) == 1
    section = payload["meaning_sections"][0]
    assert section["meaning_key"] == "bog"
    assert [item["form"] for item in section["surface_forms"]] == ["bogen", "bogens"]
    by_form = {item["form"]: item for item in section["surface_forms"]}
    assert by_form["bogen"]["english_translation"] is None
    assert by_form["bogens"]["english_translation"] is None
    assert all(item["has_pronunciation"] is False for item in section["surface_forms"])


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


def test_generate_translation_returns_generated_value(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            if text == "katten":
                return "the cat"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post(
            "/api/wordbank/translation",
            json={"surface_token": "katten", "lemma_candidate": "kat"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "generated",
        "source_word": "katten",
        "lemma": "kat",
        "english_translation": "the cat",
    }


def test_generate_translation_uses_gemini_for_gloss_aware_words(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_local_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    with sqlite3.connect(cor_local_db_path) as conn:
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
        conn.executemany(
            """
            INSERT INTO cor_entries (
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ("COR.123.111.01", "bog", "book", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),
            ),
        )
    app = create_app(_test_settings(db_path, cor_local_db_path=cor_local_db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, payload) -> str | None:
            if payload.surface_form == "bogen" and payload.lemma == "bog" and payload.gloss == "book":
                return "the book"
            return None

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "Bogen", "lemma_candidate": "bog"})
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        response = client.post(
            "/api/wordbank/translation",
            json={"surface_token": "bogen", "lemma_candidate": "bog"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "generated",
        "source_word": "bogen",
        "lemma": "bog",
        "english_translation": "the book",
    }

    with get_connection(db_path) as conn:
        surface_row = conn.execute(
            "SELECT english_translation, translation_provider FROM surface_forms WHERE form = ?",
            ("bogen",),
        ).fetchone()

    assert surface_row is not None
    assert surface_row["english_translation"] == "the book"
    assert surface_row["translation_provider"] == "gemini_word_translation"


def test_generate_translation_uses_gemini_when_azure_returns_same_text(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "azure_translator"

        def translate_da_to_en(self, text: str) -> str | None:
            if text == "mere":
                return "mere"
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return None

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, payload) -> str | None:
            if payload.surface_form == "mere" and payload.lemma == "mere":
                return "more"
            return None

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "Mere", "lemma_candidate": "mere"})
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        response = client.post(
            "/api/wordbank/translation",
            json={"surface_token": "mere", "lemma_candidate": "mere"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "generated",
        "source_word": "mere",
        "lemma": "mere",
        "english_translation": "more",
    }

    with get_connection(db_path) as conn:
        surface_row = conn.execute(
            "SELECT english_translation, translation_provider FROM surface_forms WHERE form = ?",
            ("mere",),
        ).fetchone()

    assert surface_row is not None
    assert surface_row["english_translation"] == "more"
    assert surface_row["translation_provider"] == "gemini_word_translation"


def test_get_pronunciation_audio_returns_stored_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text == "katten":
                return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav")
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", StubTTSService())
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content == b"wav-bytes"


def test_get_pronunciation_audio_normalizes_l16_to_wav(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def synthesize(self, text: str) -> PronunciationAudio | None:
            if text == "katten":
                return PronunciationAudio(
                    audio_bytes=(b"\x00\x00" * 2400),
                    mime_type="audio/l16;codec=pcm;rate=24000",
                )
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", StubTTSService())
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.content[:4] == b"RIFF"


def test_apply_verification_changes_endpoint_updates_word_fields(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )
        assert add_response.status_code == 200
        meaning_id = add_response.json()["meaning"]["id"]

        apply_response = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
                "meaning_id": meaning_id,
                "provider": "gemini",
                "suggested_changes": {
                    "lemma_pos_tag": "NOUN",
                    "lemma_morphology": "Gender=Com|Number=Sing",
                    "surface_pos_tag": "NOUN",
                    "surface_morphology": "Definite=Def|Number=Sing",
                    "lexeme_translation": "book",
                    "surface_translation": "the book",
                },
            },
        )

    assert apply_response.status_code == 200
    payload = apply_response.json()
    assert payload["status"] == "applied"
    assert set(payload["applied_fields"]) == {
        "lemma_pos_tag",
        "lemma_morphology",
        "surface_pos_tag",
        "surface_morphology",
        "lexeme_translation",
        "surface_translation",
    }

    with get_connection(db_path) as conn:
        meaning_row = conn.execute(
            """
            SELECT pos_tag, morphology, english_translation
            FROM lexeme_meanings
            WHERE id = ?
            """,
            (meaning_id,),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT pos_tag, morphology, english_translation, translation_provider
            FROM surface_forms
            WHERE meaning_id = ? AND form = ?
            """,
            (meaning_id, "bogen"),
        ).fetchone()

    assert meaning_row is not None
    assert meaning_row["pos_tag"] == "NOUN"
    assert meaning_row["morphology"] == "Gender=Com|Number=Sing"
    assert meaning_row["english_translation"] == "book"
    assert surface_row is not None
    assert surface_row["pos_tag"] == "NOUN"
    assert surface_row["morphology"] == "Definite=Def|Number=Sing"
    assert surface_row["english_translation"] == "the book"
    assert surface_row["translation_provider"] == "gemini"


def test_add_word_does_not_block_on_pronunciation_for_new_surface_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            if text == "katten":
                return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav")
            return None

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        details_response = client.get("/api/wordbank/lemmas/kat")

    assert details_response.status_code == 200
    payload = details_response.json()
    assert payload["is_sectioned"] is True
    assert payload["surface_forms"] == []
    assert len(payload["meaning_sections"]) == 1
    forms = payload["meaning_sections"][0]["surface_forms"]
    assert [item["form"] for item in forms] == ["katten"]
    assert forms[0]["english_translation"] is None
    assert forms[0]["has_pronunciation"] is False
    assert stub_tts.calls == []


def test_generate_pronunciation_endpoint_generates_for_recently_added_word(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            if text == "katten":
                return PronunciationAudio(audio_bytes=b"wav-bytes", mime_type="audio/wav")
            return None

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        pronunciation_response = client.post(
            "/api/wordbank/lexemes/pronunciation",
            json={"stored_lemma": "kat", "stored_surface_form": "katten"},
        )
        assert pronunciation_response.status_code == 200
        assert pronunciation_response.json()["status"] == "generated"

        details_response = client.get("/api/wordbank/lemmas/kat")

    assert details_response.status_code == 200
    payload = details_response.json()
    assert payload["is_sectioned"] is True
    assert payload["surface_forms"] == []
    assert len(payload["meaning_sections"]) == 1
    forms = payload["meaning_sections"][0]["surface_forms"]
    assert [item["form"] for item in forms] == ["katten"]
    assert forms[0]["english_translation"] is None
    assert forms[0]["has_pronunciation"] is True
    assert stub_tts.calls == ["kat", "katten"]


def test_generate_pronunciation_endpoint_force_regenerates_existing_audio(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTTSService:
        def __init__(self) -> None:
            self.calls: list[str] = []
            self._counter = 0

        def synthesize(self, text: str) -> PronunciationAudio | None:
            self.calls.append(text)
            if text != "katten":
                return None
            self._counter += 1
            return PronunciationAudio(audio_bytes=f"wav-{self._counter}".encode("utf-8"), mime_type="audio/wav")

    stub_tts = StubTTSService()
    with TestClient(app) as client:
        set_service_field(client.app, "tts_service", stub_tts)
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        first_response = client.post(
            "/api/wordbank/lexemes/pronunciation",
            json={"stored_lemma": "kat", "stored_surface_form": "katten"},
        )
        assert first_response.status_code == 200
        assert first_response.json()["status"] == "generated"

        second_response = client.post(
            "/api/wordbank/lexemes/pronunciation",
            json={"stored_lemma": "kat", "stored_surface_form": "katten", "force": True},
        )
        assert second_response.status_code == 200
        assert second_response.json()["status"] == "generated"

        audio_response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert audio_response.status_code == 200
    assert audio_response.content == b"wav-2"
    assert stub_tts.calls == ["kat", "katten", "kat", "katten"]


def test_get_pronunciation_audio_returns_service_unavailable_when_tts_not_configured(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200
        response = client.get("/api/wordbank/pronunciation", params={"form": "katten"})

    assert response.status_code == 503
    assert "Text-to-speech is unavailable" in response.json()["detail"]


def test_generate_translation_returns_unavailable_when_provider_has_none(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/wordbank/translation",
            json={"surface_token": "katten", "lemma_candidate": "kat"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "unavailable",
        "source_word": "katten",
        "lemma": "kat",
        "english_translation": None,
    }


def test_generate_reverse_translation_returns_generated_value(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            if text == "house":
                return "hus"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post(
            "/api/wordbank/reverse-translation",
            json={"source_word": "House"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "status": "generated",
        "source_word": "house",
        "danish_translation": "hus",
    }


def test_generate_reverse_translation_normalizes_provider_case(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            if text == "mug":
                return "Krus"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post(
            "/api/wordbank/reverse-translation",
            json={"source_word": "Mug"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "generated",
        "source_word": "mug",
        "danish_translation": "krus",
    }


def test_detect_word_language_returns_provider_detected_english(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            if text == "house":
                return "EN"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post(
            "/api/wordbank/detect-language",
            json={"source_word": "House"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "source_word": "house",
        "language": "en",
        "confidence": 0.82,
    }


def test_detect_word_language_returns_danish_for_danish_chars(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post(
            "/api/wordbank/detect-language",
            json={"source_word": "børn"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "source_word": "børn",
        "language": "da",
        "confidence": 0.99,
    }


def test_generate_phrase_translation_returns_cached_value_without_second_provider_call(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def __init__(self) -> None:
            self.calls = 0

        def translate_da_to_en(self, text: str) -> str | None:
            self.calls += 1
            if text == "jeg kan godt lide det":
                return "i like it"
            return None

    stub_service = StubTranslationService()
    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", stub_service)
        first_response = client.post(
            "/api/wordbank/phrase-translation",
            json={"source_text": "Jeg kan godt lide det"},
        )
        second_response = client.post(
            "/api/wordbank/phrase-translation",
            json={"source_text": "  jeg   kan godt   lide det "},
        )

    assert first_response.status_code == 200
    assert first_response.json() == {
        "status": "generated",
        "source_text": "jeg kan godt lide det",
        "english_translation": "i like it",
    }
    assert second_response.status_code == 200
    assert second_response.json() == {
        "status": "cached",
        "source_text": "jeg kan godt lide det",
        "english_translation": "i like it",
    }
    assert stub_service.calls == 1


def test_add_sentence_inserts_and_returns_translation_from_provider(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            if text == "Jeg elsker kaffe":
                return "i love coffee"
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post(
            "/api/sentencebank/sentences",
            json={"source_text": "Jeg elsker kaffe"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "status": "inserted",
        "source_text": "Jeg elsker kaffe",
        "english_translation": "i love coffee",
        "message": 'Added "Jeg elsker kaffe" to sentencebank.',
    }


def test_add_sentence_duplicate_is_graceful(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        first = client.post("/api/sentencebank/sentences", json={"source_text": "Jeg laeser hver dag"})
        second = client.post("/api/sentencebank/sentences", json={"source_text": "  jeg   laeser hver dag "})

    assert first.status_code == 200
    assert first.json()["status"] == "inserted"

    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["status"] == "exists"
    assert "already" in second_payload["message"].lower()


def test_list_sentences_returns_newest_first(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/sentencebank/sentences", json={"source_text": "Jeg laeser en bog"})
        client.post("/api/sentencebank/sentences", json={"source_text": "Vi spiser nu"})
        response = client.get("/api/sentencebank/sentences")

    assert response.status_code == 200
    payload = response.json()
    assert [item["source_text"] for item in payload["items"]] == ["Vi spiser nu", "Jeg laeser en bog"]

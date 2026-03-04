from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

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
        client.app.state.word_verification_service = StubVerificationService()
        response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Bogen", "lemma_candidate": "bog"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["verification"]["status"] == "queued"
    assert payload["verification"]["provider"] == "gemini"
    assert payload["verification"]["reviewer_role"] == "Professional Danish Language Expert"

    with TestClient(app) as client:
        client.app.state.word_verification_service = StubVerificationService()
        verify_response = client.post(
            "/api/wordbank/lexemes/verify",
            json={"stored_lemma": "bog", "stored_surface_form": "bogen"},
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


def test_search_lemmas_returns_variation_matches(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        response = client.get("/api/wordbank/search", params={"query": "gens"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["items"] == [
        {
            "lemma": "bog",
            "display_lemma": "bog",
            "english_translation": None,
            "variation_count": 2,
            "match_surface": "bogens",
            "pos_tag": None,
            "morphology": None,
        }
    ]


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
    assert payload["items"] == [
        {
            "lemma": "ulykke",
            "display_lemma": "ulykke",
            "english_translation": None,
            "variation_count": 2,
            "match_surface": "ulykker",
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Plur|Definite=Ind",
        }
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
        response = client.get("/api/wordbank/search/cor-form", params={"form": "LÆRER"})

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
        response = client.get("/api/wordbank/search/cor-form", params={"form": "lærer"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["form"] == "lærer"
    assert len(payload["groups"]) == 2


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
    assert [item["form"] for item in payload["surface_forms"]] == ["bog", "bogen", "bogens"]
    by_form = {item["form"]: item for item in payload["surface_forms"]}
    assert by_form["bog"]["english_translation"] is None
    assert by_form["bogen"]["english_translation"] is None
    assert by_form["bogens"]["english_translation"] is None
    assert all(item["has_pronunciation"] is False for item in payload["surface_forms"])


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
        client.app.state.translation_service = StubTranslationService()
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
        client.app.state.tts_service = StubTTSService()
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
        client.app.state.tts_service = StubTTSService()
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

        apply_response = client.post(
            "/api/wordbank/lexemes/apply-verification-changes",
            json={
                "stored_lemma": "bog",
                "stored_surface_form": "bogen",
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
        lexeme_row = conn.execute(
            "SELECT pos_tag, morphology, english_translation, translation_provider FROM lexemes WHERE lemma = ?",
            ("bog",),
        ).fetchone()
        surface_row = conn.execute(
            """
            SELECT pos_tag, morphology, english_translation, translation_provider
            FROM surface_forms
            WHERE form = ?
            """,
            ("bogen",),
        ).fetchone()

    assert lexeme_row is not None
    assert lexeme_row["pos_tag"] == "NOUN"
    assert lexeme_row["morphology"] == "Gender=Com|Number=Sing"
    assert lexeme_row["english_translation"] == "book"
    assert lexeme_row["translation_provider"] == "gemini"
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
        client.app.state.tts_service = stub_tts
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "Katten", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200

        details_response = client.get("/api/wordbank/lemmas/kat")

    assert details_response.status_code == 200
    payload = details_response.json()
    assert payload["surface_forms"] == [
        {
            "form": "katten",
            "english_translation": None,
            "pos_tag": None,
            "morphology": None,
            "has_pronunciation": False,
        }
    ]
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
        client.app.state.tts_service = stub_tts
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
    assert payload["surface_forms"] == [
        {
            "form": "katten",
            "english_translation": None,
            "pos_tag": None,
            "morphology": None,
            "has_pronunciation": True,
        }
    ]
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
        client.app.state.tts_service = stub_tts
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
        client.app.state.translation_service = StubTranslationService()
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
        client.app.state.translation_service = StubTranslationService()
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
        client.app.state.translation_service = StubTranslationService()
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
        client.app.state.translation_service = stub_service
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
        client.app.state.translation_service = StubTranslationService()
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

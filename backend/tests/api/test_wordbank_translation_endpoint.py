from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.db.migrations import apply_migrations, get_connection
from app.main import create_app
from tests.api.support import build_api_test_app
from tests.api.wordbank_test_support import build_test_settings


def test_generate_translation_returns_generated_value(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return "the cat" if text == "katten" else None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/wordbank/translation", json={"surface_token": "katten", "lemma_candidate": "kat"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "generated",
        "source_word": "katten",
        "lemma": "kat",
        "english_translation": "the cat",
    }


def test_generate_translation_uses_gemini_for_gloss_aware_words(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_local_db_path = tmp_path / "cor.sqlite"
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
            (("COR.123.111.01", "bog", "book", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),),
        )
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=stub_nlp_adapter_factory,
        cor_local_db_path=cor_local_db_path,
    )

    class StubGeminiWordTranslationService:
        provider = "gemini_word_translation"

        def translate_word(self, payload) -> str | None:
            if payload.surface_form == "bogen" and payload.lemma == "bog" and payload.gloss == "book":
                return "the book"
            return None

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "Bogen", "lemma_candidate": "bog"})
        set_service_field(client.app, "gemini_word_translation_service", StubGeminiWordTranslationService())
        response = client.post("/api/wordbank/translation", json={"surface_token": "bogen", "lemma_candidate": "bog"})

    assert response.status_code == 200
    assert response.json()["english_translation"] == "the book"
    with get_connection(db_path) as conn:
        surface_row = conn.execute("SELECT form FROM surface_forms WHERE form = ?", ("bogen",)).fetchone()
    assert surface_row is not None


def test_generate_translation_strips_provider_frame_context_for_single_words(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_local_db_path = tmp_path / "cor.sqlite"
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
            (("COR.321.111.01", "med", None, "præp", "med", "N", 321, 111, 1),),
        )
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=stub_nlp_adapter_factory,
        cor_local_db_path=cor_local_db_path,
    )

    class StubTranslationService:
        provider = "deepl_translator"

        def translate_da_to_en(self, text: str) -> str | None:
            return "with the house" if text == "med huset" else None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/wordbank/translation", json={"surface_token": "med", "lemma_candidate": "med"})

    assert response.status_code == 200
    assert response.json()["english_translation"] == "with"


def test_generate_translation_uses_gemini_when_azure_returns_same_text(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "azure_translator"

        def translate_da_to_en(self, text: str) -> str | None:
            return "mere" if text == "mere" else None

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
        response = client.post("/api/wordbank/translation", json={"surface_token": "mere", "lemma_candidate": "mere"})

    assert response.status_code == 200
    assert response.json()["english_translation"] == "more"


def test_generate_translation_returns_unavailable_when_provider_has_none(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post("/api/wordbank/translation", json={"surface_token": "katten", "lemma_candidate": "kat"})

    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"
    assert response.json()["english_translation"] is None


def test_generate_reverse_translation_returns_generated_value(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return "hus" if text == "house" else None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/wordbank/reverse-translation", json={"source_word": "House"})

    assert response.status_code == 200
    assert response.json() == {"status": "generated", "source_word": "house", "danish_translation": "hus"}


def test_generate_reverse_translation_normalizes_provider_case(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return "Krus" if text == "mug" else None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/wordbank/reverse-translation", json={"source_word": "Mug"})

    assert response.status_code == 200
    assert response.json()["danish_translation"] == "krus"


def test_detect_word_language_returns_provider_detected_english(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return "EN" if text == "house" else None

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        response = client.post("/api/wordbank/detect-language", json={"source_word": "House"})

    assert response.status_code == 200
    assert response.json() == {"source_word": "house", "language": "en", "confidence": 0.82}


def test_detect_word_language_returns_danish_for_danish_chars(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        response = client.post("/api/wordbank/detect-language", json={"source_word": "børn"})

    assert response.status_code == 200
    assert response.json() == {"source_word": "børn", "language": "da", "confidence": 0.99}


def test_generate_phrase_translation_returns_cached_value_without_second_provider_call(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    app = create_app(build_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        def __init__(self) -> None:
            self.calls = 0

        def translate_da_to_en(self, text: str) -> str | None:
            self.calls += 1
            return "i like it" if text == "Jeg kan godt lide det" else None

    stub_service = StubTranslationService()
    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", stub_service)
        first_response = client.post("/api/wordbank/phrase-translation", json={"source_text": "Jeg kan godt lide det"})
        second_response = client.post("/api/wordbank/phrase-translation", json={"source_text": "  jeg   kan godt   lide det "})

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json()["status"] == "generated"
    assert second_response.json()["status"] == "cached"
    assert stub_service.calls == 1

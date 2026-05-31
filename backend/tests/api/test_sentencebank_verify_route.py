from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.services.sentence_verification import (
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
)
from tests.api.support import build_api_test_app


class StubSentenceVerificationService:
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        if source_text == "jeg er glat":
            return SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=7, end=11, message="typo")],
                corrected_text="jeg er glad",
                language="da",
            )
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="da",
        )


def test_verify_sentence_valid(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", StubSentenceVerificationService())
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glad"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is True
    assert body["errors"] == []
    assert body["corrected_text"] is None
    assert body["language"] == "da"


def test_verify_sentence_with_errors(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", StubSentenceVerificationService())
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glat"})
    assert response.status_code == 200
    body = response.json()
    assert body["is_valid"] is False
    assert body["errors"] == [{"start": 7, "end": 11, "message": "typo"}]
    assert body["corrected_text"] == "jeg er glad"
    assert body["language"] == "da"


def test_verify_sentence_no_service_returns_valid(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        set_service_field(client.app, "sentence_verification_service", None)
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": "jeg er glad"})
    assert response.status_code == 200
    assert response.json()["is_valid"] is True


def test_verify_sentence_too_long_returns_422(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        response = client.post(
            "/api/sentencebank/verify-sentence",
            json={"source_text": "a" * 101},
        )
    assert response.status_code == 422


def test_verify_sentence_empty_returns_422(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)
    with TestClient(app) as client:
        response = client.post("/api/sentencebank/verify-sentence", json={"source_text": ""})
    assert response.status_code == 422


class StubSentencePreviewVerificationService:
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        if source_text == "I am happy":
            return SentenceVerificationResult(
                is_valid=True,
                errors=[],
                corrected_text=None,
                language="en",
            )
        if source_text == "jeg er glat":
            return SentenceVerificationResult(
                is_valid=False,
                errors=[SentenceVerificationErrorSpan(start=7, end=11, message="typo")],
                corrected_text="jeg er glad",
                language="da",
            )
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="da",
        )


def test_sentence_search_preview_returns_danish_preview(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "stub"

        def translate_da_to_en(self, text: str) -> str | None:
            return "i am happy" if text == "jeg er glad" else None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return "DA"

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "sentence_verification_service", StubSentencePreviewVerificationService())
        response = client.post("/api/sentencebank/search-preview", json={"source_text": "jeg er glat"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["query_language"] == "da"
    assert data["source_text"] == "jeg er glad"
    assert data["english_translation"] == "I am happy"
    assert data["is_valid"] is False
    assert data["corrected_text"] == "jeg er glad"
    assert data["errors"] == [{"start": 7, "end": 11, "message": "typo"}]
    assert data["message"] is None


def test_sentence_search_preview_translates_english_to_danish(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "stub"

        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return "jeg er glad" if text == "I am happy" else None

        def detect_source_language(self, text: str) -> str | None:
            return "EN" if text == "I am happy" else "DA"

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "sentence_verification_service", StubSentencePreviewVerificationService())
        response = client.post("/api/sentencebank/search-preview", json={"source_text": "I am happy"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["query_language"] == "en"
    assert data["source_text"] == "jeg er glad"
    assert data["english_translation"] == "I am happy"
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["message"] is None


def test_sentence_search_preview_fast_mode_returns_preview_status(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "stub"

        def translate_da_to_en(self, text: str) -> str | None:
            return "i am happy" if text == "jeg er glad" else None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return "DA"

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "sentence_verification_service", StubSentencePreviewVerificationService())
        response = client.post(
            "/api/sentencebank/search-preview",
            json={"source_text": "jeg er glad", "fast": True},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "preview"
    assert data["query_language"] == "da"
    assert data["source_text"] == "jeg er glad"
    assert data["english_translation"] == "I am happy"
    assert data["is_valid"] is True
    assert data["errors"] == []
    assert data["message"] is None


def test_sentence_search_preview_blocks_when_english_cannot_translate(tmp_path, stub_nlp_adapter_factory) -> None:
    app = build_api_test_app(tmp_path / "db.sqlite3", nlp_adapter_factory=stub_nlp_adapter_factory)

    class StubTranslationService:
        provider = "stub"

        def translate_da_to_en(self, text: str) -> str | None:
            return None

        def translate_en_to_da(self, text: str) -> str | None:
            return None

        def detect_source_language(self, text: str) -> str | None:
            return "EN"

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        set_service_field(client.app, "sentence_verification_service", StubSentencePreviewVerificationService())
        response = client.post("/api/sentencebank/search-preview", json={"source_text": "I am happy"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked"
    assert data["query_language"] == "en"
    assert data["source_text"] is None
    assert data["english_translation"] is None
    assert data["is_valid"] is False
    assert data["errors"] == []
    assert data["message"] == "Could not translate this English sentence to Danish."

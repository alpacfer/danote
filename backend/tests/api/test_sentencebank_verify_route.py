from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.services.sentence_verification import SentenceVerificationErrorSpan, SentenceVerificationResult
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

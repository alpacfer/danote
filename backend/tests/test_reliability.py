from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.nlp.adapter import NLPToken


def _settings(db_path) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_trf-0.2.0",
        translation_enabled=False,
    )


class SimpleAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        tokens: list[NLPToken] = []
        for raw in text.split():
            is_punctuation = bool(re.fullmatch(r"[^\w]+", raw, flags=re.UNICODE))
            tokens.append(
                NLPToken(
                    text=raw,
                    lemma=raw.lower() if not is_punctuation else None,
                    pos=None,
                    morphology=None,
                    is_punctuation=is_punctuation,
                )
            )
        return tokens

    def lemma_for_token(self, token: str) -> str | None:
        cleaned = token.strip().lower()
        return cleaned or None

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        lemma = self.lemma_for_token(token)
        return [lemma] if lemma else []

    def metadata(self) -> dict[str, str]:
        return {"adapter": "SimpleAdapter"}


def _simple_adapter_factory(_settings: Settings) -> SimpleAdapter:
    return SimpleAdapter()


def test_word_persists_across_backend_restart(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    settings = _settings(db_path)

    app_first = create_app(settings=settings, nlp_adapter_factory=_simple_adapter_factory)
    with TestClient(app_first) as client:
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "kat", "lemma_candidate": "kat"},
        )
        assert add_response.status_code == 200
        assert add_response.json()["status"] == "inserted"

    app_second = create_app(settings=settings, nlp_adapter_factory=_simple_adapter_factory)
    with TestClient(app_second) as client:
        analyze_response = client.post("/api/analyze", json={"text": "kat"})

    assert analyze_response.status_code == 200
    tokens = analyze_response.json()["tokens"]
    assert len(tokens) == 1
    assert tokens[0]["normalized_token"] == "kat"
    assert tokens[0]["classification"] == "known"


def test_invalid_db_path_marks_backend_degraded_and_returns_user_facing_message(tmp_path) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    settings = _settings(blocked_parent / "danote.sqlite3")

    app = create_app(settings=settings, nlp_adapter_factory=_simple_adapter_factory)
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        analyze_response = client.post("/api/analyze", json={"text": "kat"})
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "kat", "lemma_candidate": "kat"},
        )

    assert health_response.status_code == 200
    health = health_response.json()
    assert health["status"] == "degraded"
    assert health["components"]["database"] == "degraded"
    assert health["components"]["nlp"] == "ok"

    assert analyze_response.status_code == 503
    assert "Database unavailable" in analyze_response.json()["detail"]
    assert add_response.status_code == 503
    assert "Database unavailable" in add_response.json()["detail"]


def test_nlp_init_failure_marks_backend_degraded_and_analysis_unavailable(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    settings = _settings(db_path)

    def failing_nlp_factory(_settings: Settings):
        raise RuntimeError("nlp init failed")

    app = create_app(settings=settings, nlp_adapter_factory=failing_nlp_factory)
    with TestClient(app) as client:
        health_response = client.get("/api/health")
        analyze_response = client.post("/api/analyze", json={"text": "kat"})
        add_response = client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "kat", "lemma_candidate": "kat"},
        )

    assert health_response.status_code == 200
    health = health_response.json()
    assert health["status"] == "degraded"
    assert health["components"]["database"] == "ok"
    assert health["components"]["nlp"] == "degraded"

    assert analyze_response.status_code == 503
    assert "NLP unavailable" in analyze_response.json()["detail"]
    # Wordbank writes should still be available when only NLP is degraded.
    assert add_response.status_code == 200

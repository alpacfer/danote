from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import analyze as analyze_routes
from app.core.app_state import init_app_state, set_runtime_field
from app.core.config import Settings


class _FakeWordbankUseCase:
    def __init__(self, *, should_fail: bool = False):
        self.should_fail = should_fail
        self.calls: list[dict[str, object]] = []

    def resolve_query(
        self,
        query_text: str,
        *,
        include_translations: bool = True,
        include_language_detection: bool = True,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "query_text": query_text,
                "include_translations": include_translations,
                "include_language_detection": include_language_detection,
            }
        )
        if self.should_fail:
            raise ValueError("query_text is required")

        return {
            "query_surface": query_text.lower(),
            "query_lemma": query_text.lower(),
            "classification": "new",
            "matched_lemma": None,
            "matched_lemma_summary": None,
            "query_pos_tag": None,
            "query_morphology": None,
            "resolved_surface": query_text.lower(),
            "resolved_lemma": query_text.lower(),
            "da_to_en_translation": None,
            "en_to_da_translation": None,
            "en_to_da_lemma": None,
            "en_to_da_pos_tag": None,
            "en_to_da_morphology": None,
            "query_language": None,
            "query_language_confidence": None,
            "word_actions": [],
        }


def _build_test_client(
    fake_use_case: _FakeWordbankUseCase,
    monkeypatch: pytest.MonkeyPatch,
    *,
    db_ready: bool = True,
) -> TestClient:
    app = FastAPI()
    app.include_router(analyze_routes.router, prefix="/api")
    init_app_state(
        app,
        Settings(
            environment="test",
            app_name="danote-backend-test",
            host="127.0.0.1",
            port=8001,
            db_path=Path("/tmp/danote-test.sqlite3"),
            nlp_model="stub",
        ),
    )
    set_runtime_field(app, "db_ready", db_ready)

    def _fake_factory(_request):
        return fake_use_case

    app.dependency_overrides = {}
    monkeypatch.setattr(analyze_routes, "build_wordbank_use_case", _fake_factory)
    return TestClient(app)


def test_enrich_token_uses_route_factory_and_forwards_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_use_case = _FakeWordbankUseCase()
    with _build_test_client(fake_use_case, monkeypatch) as client:
        response = client.post(
            "/api/analyze/enrich-token",
            json={
                "token": "House",
                "include_translations": False,
                "include_language_detection": False,
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["query_surface"] == "house"
    assert fake_use_case.calls == [
        {
            "query_text": "House",
            "include_translations": False,
            "include_language_detection": False,
        }
    ]


def test_enrich_token_maps_value_error_to_400(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_use_case = _FakeWordbankUseCase(should_fail=True)
    with _build_test_client(fake_use_case, monkeypatch) as client:
        response = client.post("/api/analyze/enrich-token", json={"token": "House"})

    assert response.status_code == 400
    assert response.json()["detail"] == "query_text is required"


def test_enrich_token_returns_503_when_db_not_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_use_case = _FakeWordbankUseCase()
    with _build_test_client(fake_use_case, monkeypatch, db_ready=False) as client:
        response = client.post("/api/analyze/enrich-token", json={"token": "House"})

    assert response.status_code == 503
    assert "Database unavailable" in response.json()["detail"]
    assert fake_use_case.calls == []

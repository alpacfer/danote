from __future__ import annotations

from fastapi.testclient import TestClient

from app.bootstrap.runtime import default_nlp_adapter_factory
from app.db.seed import seed_starter_data
from tests.api.support import build_api_test_app

MODEL = "da_dacy_small_trf-0.2.0"


def test_real_nlp_analysis_endpoint_lemmatizes_bogen_to_bog(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=default_nlp_adapter_factory,
        apply_db_migrations=True,
    )
    seed_starter_data(db_path)
    with TestClient(app) as client:
        response = client.post("/api/analyze", json={"text": "Jeg kan lide bogen"})

    assert response.status_code == 200
    by_token = {item["normalized_token"]: item for item in response.json()["tokens"]}
    assert by_token["bogen"]["lemma_candidate"] == "bog"


def test_real_nlp_analysis_endpoint_handles_punctuation_only_safely(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=default_nlp_adapter_factory,
        apply_db_migrations=True,
    )
    seed_starter_data(db_path)
    with TestClient(app) as client:
        response = client.post("/api/analyze", json={"text": "!!!"})

    assert response.status_code == 200
    assert response.json() == {"tokens": []}

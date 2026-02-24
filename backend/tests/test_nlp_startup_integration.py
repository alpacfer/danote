from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


MODEL = "da_dacy_small_tft-0.0.0"


def test_backend_startup_loads_nlp_pipeline_and_exposes_metadata(tmp_path) -> None:
    settings = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=tmp_path / "danote.sqlite3",
        nlp_model=MODEL,
    )

    app = create_app(settings=settings)

    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200

    metadata = app.state.nlp_adapter.metadata()
    assert metadata["model"] == MODEL
    assert "spacy" in metadata
    assert "dacy" in metadata
    assert "lemmy" in metadata

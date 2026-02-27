from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data
from app.main import create_app


MODEL = "da_dacy_small_trf-0.2.0"


@pytest.fixture(scope="module")
def analysis_client(tmp_path_factory) -> TestClient:
    tmp_dir = tmp_path_factory.mktemp("analysis-endpoint")
    db_path = tmp_dir / "danote.sqlite3"

    apply_migrations(db_path)
    seed_starter_data(db_path)

    settings = Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model=MODEL,
    )

    app = create_app(settings=settings)
    with TestClient(app) as client:
        yield client


def test_text_input_returns_token_results(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "Jeg kan godt lide bogen"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["tokens"], list)

    by_token = {item["normalized_token"]: item for item in payload["tokens"]}
    assert by_token["kan"]["classification"] == "known"
    assert by_token["lide"]["classification"] == "known"
    assert by_token["bogen"]["classification"] == "variation"
    assert by_token["bogen"]["match_source"] == "lemma"
    assert by_token["bogen"]["status"] == "variation"


def test_punctuation_not_returned_as_normal_words(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "!!! ... ???"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload == {"tokens": []}


def test_repeated_whitespace_and_newlines_do_not_break_output(
    analysis_client: TestClient,
) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "\n\n  kan   \n   lide\n\n"},
    )

    assert response.status_code == 200
    normalized = [item["normalized_token"] for item in response.json()["tokens"]]
    assert normalized == ["kan", "lide"]


def test_response_matches_contract_schema_exactly(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "kan"})

    assert response.status_code == 200
    payload = response.json()
    assert set(payload.keys()) == {"tokens"}
    assert len(payload["tokens"]) == 1

    token = payload["tokens"][0]
    assert set(token.keys()) == {
        "surface_token",
        "normalized_token",
        "lemma_candidate",
        "pos_tag",
        "morphology",
        "classification",
        "match_source",
        "matched_lemma",
        "matched_surface_form",
        "suggestions",
        "confidence",
        "reason_tags",
        "status",
        "surface",
        "normalized",
        "lemma",
        "pos_tag",
        "morphology",
    }




def test_response_includes_pos_and_morphology_fields(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "kan"})

    assert response.status_code == 200
    token = response.json()["tokens"][0]
    assert "pos_tag" in token
    assert "morphology" in token

def test_empty_and_newline_heavy_input_safe(analysis_client: TestClient) -> None:
    for text in ["", "\n\n\n   \n"]:
        response = analysis_client.post("/api/analyze", json={"text": text})
        assert response.status_code == 200
        assert response.json() == {"tokens": []}


def test_symbol_only_tokens_are_filtered_but_numbers_remain(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "🙂 2 > kan ✅"},
    )

    assert response.status_code == 200
    normalized = [item["normalized_token"] for item in response.json()["tokens"]]
    assert normalized == ["2", "kan"]


def test_typo_token_is_not_silently_classified_as_new(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "spisr"},
    )

    assert response.status_code == 200
    token = response.json()["tokens"][0]
    assert token["classification"] == "typo_likely"
    assert token["suggestions"]

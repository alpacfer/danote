from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.core.app_state import set_runtime_field
from app.nlp.adapter import NLPToken
from app.db.seed import seed_starter_data
from tests.api.support import build_api_test_app


class FakeAnalysisNLPAdapter:
    _LEMMA_OVERRIDES = {
        "bogen": "bog",
        "bogens": "bog",
        "spisr": "spisr",
    }

    _TOKEN_METADATA = {
        "kan": ("AUX", "Mood=Ind|Tense=Pres|VerbForm=Fin"),
        "lide": ("VERB", "VerbForm=Inf"),
        "bogen": ("NOUN", "Gender=Com|Number=Sing|Definite=Def"),
        "bogens": ("NOUN", "Gender=Com|Number=Sing|Definite=Def|Case=Gen"),
        "spisr": ("VERB", "VerbForm=Fin"),
        "jeg": ("PRON", "Case=Nom|Person=1|PronType=Prs"),
    }

    def tokenize(self, text: str) -> list[NLPToken]:
        tokens: list[NLPToken] = []
        for match in re.finditer(r"\d+|[^\W\d_]+|[^\s\w]+", text, re.UNICODE):
            value = match.group(0)
            normalized = value.lower()
            pos, morphology = self._TOKEN_METADATA.get(normalized, ("X", None))
            tokens.append(
                NLPToken(
                    text=value,
                    lemma=self.lemma_for_token(value),
                    pos=pos,
                    morphology=morphology,
                    is_punctuation=not value.isalnum(),
                )
            )
        return tokens

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        lemma = self.lemma_for_token(token)
        return [lemma] if lemma else []

    def lemma_for_token(self, token: str) -> str | None:
        normalized = token.strip().lower()
        if not normalized:
            return None
        return self._LEMMA_OVERRIDES.get(normalized, normalized)

    def metadata(self) -> dict[str, str]:
        return {"adapter": "fake-analysis"}


@pytest.fixture(scope="module")
def analysis_client(tmp_path_factory) -> TestClient:
    tmp_dir = tmp_path_factory.mktemp("analysis-endpoint")
    db_path = tmp_dir / "danote.sqlite3"
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=lambda _settings: FakeAnalysisNLPAdapter(),
        apply_db_migrations=True,
    )
    seed_starter_data(db_path)
    with TestClient(app) as client:
        yield client


def test_text_input_returns_token_results(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "Jeg kan godt lide bogen"})

    assert response.status_code == 200
    payload = response.json()
    by_token = {item["normalized_token"]: item for item in payload["tokens"]}
    assert by_token["kan"]["classification"] == "known"
    assert by_token["lide"]["classification"] == "known"
    assert by_token["bogen"]["classification"] == "variation"
    assert by_token["bogen"]["match_source"] == "lemma"


def test_punctuation_not_returned_as_normal_words(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "!!! ... ???"})
    assert response.status_code == 200
    assert response.json() == {"tokens": []}


def test_repeated_whitespace_and_newlines_do_not_break_output(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "\n\n  kan   \n   lide\n\n"})
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
        "word_actions",
    }


def test_response_includes_pos_and_morphology_fields(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "kan"})
    assert response.status_code == 200
    token = response.json()["tokens"][0]
    assert token["pos_tag"] == "AUX"
    assert token["morphology"] == "Mood=Ind|Tense=Pres|VerbForm=Fin"


def test_empty_and_newline_heavy_input_safe(analysis_client: TestClient) -> None:
    for text in ["", "\n\n\n   \n"]:
        response = analysis_client.post("/api/analyze", json={"text": text})
        assert response.status_code == 200
        assert response.json() == {"tokens": []}


def test_symbol_only_tokens_are_filtered_but_numbers_remain(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "🙂 2 > kan ✅"})
    assert response.status_code == 200
    normalized = [item["normalized_token"] for item in response.json()["tokens"]]
    assert normalized == ["2", "kan"]


def test_typo_token_is_not_silently_classified_as_new(analysis_client: TestClient) -> None:
    response = analysis_client.post("/api/analyze", json={"text": "spisr"})
    assert response.status_code == 200
    token = response.json()["tokens"][0]
    assert token["classification"] == "typo_likely"
    assert token["suggestions"]


def test_hash_comments_are_ignored_on_each_line(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze",
        json={"text": "kan # ignore this\nlide # also ignored"},
    )
    assert response.status_code == 200
    normalized = [item["normalized_token"] for item in response.json()["tokens"]]
    assert normalized == ["kan", "lide"]


def test_enrich_token_returns_resolve_payload(analysis_client: TestClient) -> None:
    response = analysis_client.post(
        "/api/analyze/enrich-token",
        json={"token": "bogen", "include_translations": False, "include_language_detection": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["query_surface"] == "bogen"
    assert payload["classification"] in {"known", "variation", "new", "typo_likely", "uncertain"}
    assert "word_actions" in payload


def test_enrich_token_requires_db_ready(analysis_client: TestClient) -> None:
    set_runtime_field(analysis_client.app, "db_ready", False)
    response = analysis_client.post("/api/analyze/enrich-token", json={"token": "bogen"})
    assert response.status_code == 503
    set_runtime_field(analysis_client.app, "db_ready", True)

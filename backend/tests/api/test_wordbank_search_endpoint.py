from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.app_state import set_service_field
from app.services.cor_local import CORLocalEntry
from app.db.migrations import apply_migrations
from app.main import create_app
from tests.api.support import build_api_test_app
from tests.api.wordbank_test_support import (
    build_test_settings,
    seed_cor_local_bog_senses,
    seed_cor_local_db,
    seed_cor_local_word_page_gloss_cases,
)
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeGeminiWordTranslationService,
    FakeTranslationService,
)


def test_search_lemmas_returns_variation_matches(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})
        response = client.get("/api/wordbank/search", params={"query": "gens"})

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["lemma"] == "bog"
    assert item["display_lemma"] == "bog"
    assert item["meaning_key"] == "bog"
    assert item["variation_count"] == 2
    assert item["match_surface"] == "bogens"
    assert item["query_cor_ids"] == []
    assert item["pos_tag"] is None
    assert item["morphology"] is None


def test_search_lemmas_prefers_matched_surface_metadata(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

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
    item = response.json()["items"][0]
    assert item["lemma"] == "ulykke"
    assert item["meaning_key"] == "ulykke"
    assert item["match_surface"] == "ulykker"
    assert item["pos_tag"] == "NOUN"
    assert item["morphology"] == "Gender=Com|Number=Plur|Definite=Ind"


def test_search_lemmas_returns_query_cor_ids_for_exact_form(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    seed_cor_local_bog_senses(cor_db_path)
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=stub_nlp_adapter_factory,
        cor_local_db_path=cor_db_path,
    )

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )
        response = client.get("/api/wordbank/search", params={"query": "bogen"})

    assert response.status_code == 200
    assert [(item["meaning_key"], item["query_cor_ids"], item["cor_lemma_idx"]) for item in response.json()["items"]] == [
        ("book", ["COR.BOG.BOOK.1"], 123),
        ("swamp", ["COR.BOG.SWAMP.1"], 124),
    ]


def test_search_lemmas_returns_two_rows_for_exact_homograph_lemma(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    seed_cor_local_bog_senses(cor_db_path)
    app = build_api_test_app(
        db_path,
        nlp_adapter_factory=stub_nlp_adapter_factory,
        cor_local_db_path=cor_db_path,
    )

    with TestClient(app) as client:
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.BOOK.1"},
        )
        client.post(
            "/api/wordbank/lexemes",
            json={"surface_token": "bogen", "lemma_candidate": "bog", "cor_id": "COR.BOG.SWAMP.1"},
        )
        response = client.get("/api/wordbank/search", params={"query": "bog"})

    assert response.status_code == 200
    assert [(item["meaning_key"], item["match_surface"], item["english_translation"]) for item in response.json()["items"]] == [
        ("book", "bog", "book"),
        ("swamp", "bog", "swamp"),
    ]


def test_search_lemmas_returns_gloss_translation_without_promoting_it_to_english_translation(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_word_page_gloss_cases(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    class StubTranslationService:
        def translate_da_to_en(self, text: str) -> str | None:
            return {
                "jordlag": "soil layer",
            }.get(text)

    with TestClient(app) as client:
        set_service_field(client.app, "translation_service", StubTranslationService())
        save_response = client.post(
            "/api/wordbank/lexemes",
            json={
                "surface_token": "mor",
                "lemma_candidate": "mor",
                "search_seed": {
                    "lemma": "mor",
                    "surface": "mor",
                    "cor_id": "COR.MOR.SOIL.LEM",
                    "cor_lemma_idx": 51047,
                    "meaning_key": "soil-layer",
                    "gloss": "jordlag",
                    "english_translation": "mother",
                    "pos_tag": "NOUN",
                    "morphology": "Gender=Com|Number=Sing|Definite=Ind",
                },
            },
        )
        response = client.get("/api/wordbank/search", params={"query": "mor"})

    assert save_response.status_code == 200
    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "lemma": "mor",
            "display_lemma": "mor",
            "meaning_id": 1,
            "meaning_key": "soil-layer",
            "gloss": "jordlag",
            "gloss_translation": "soil layer",
            "cor_lemma_idx": 51047,
            "english_translation": "mother",
            "variation_count": 1,
            "match_surface": "mor",
            "query_cor_ids": ["COR.MOR.SOIL.LEM"],
            "pos_tag": "NOUN",
            "morphology": "Gender=Com|Number=Sing|Definite=Ind",
        }
    ]


def test_search_cor_form_returns_grouped_variants(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "LÆRER", "include_translations": "false"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["form"] == "lærer"
    by_key = {(item["lemma"], item["pos_tag"]): item for item in payload["groups"]}
    assert by_key[("lærer", "NOUN")]["gloss"] == "teacher"
    assert by_key[("lære", "VERB")]["gloss"] == "learn"


def test_search_cor_form_hides_self_translation_until_gemini_has_real_translation(
    tmp_path,
    stub_nlp_adapter_factory,
) -> None:
    db_path = tmp_path / "danote.sqlite3"
    app = build_api_test_app(db_path, nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        set_service_field(
            client.app,
            "cor_local_lexicon_service",
            FakeCORLocalLexiconService(
                by_form={
                    "bil": [
                        CORLocalEntry(
                            cor_id="COR.36439.209.01",
                            lemma="bile",
                            gloss="køre i bil",
                            gram_raw="vb.imp",
                            form="bil",
                            norm="N",
                            lemma_idx=36439,
                            gram_code=209,
                            variation=1,
                            pos_tag="VERB",
                            morphology="Mood=Imp|VerbForm=Fin",
                            features={"Mood": "Imp", "VerbForm": "Fin"},
                            extra_tags=[],
                        ),
                    ]
                }
            ),
        )
        set_service_field(
            client.app,
            "translation_service",
            FakeTranslationService({"at bile": "to bile", "køre i bil": "go by car"}),
        )
        set_service_field(
            client.app,
            "gemini_word_translation_service",
            FakeGeminiWordTranslationService(
                {("bil", "bile", "køre i bil"): None},
                batch_overrides={("bil", "bile", "køre i bil"): None},
            ),
        )

        response = client.get("/api/wordbank/search/cor-form", params={"form": "bil"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["groups"] == [
        {
            "lemma": "bile",
            "gloss": "køre i bil",
            "pos_tag": "VERB",
            "variants": [
                {
                    "cor_id": "COR.36439.209.01",
                    "form": "bil",
                    "lemma": "bile",
                    "gloss": "køre i bil",
                    "gloss_translation": "go by car",
                    "lemma_translation": None,
                    "gram_raw": "vb.imp",
                    "norm": "N",
                    "lemma_idx": 36439,
                    "gram_code": 209,
                    "variation": 1,
                    "pos_tag": "VERB",
                    "morphology": "Mood=Imp|VerbForm=Fin",
                    "features": {"Mood": "Imp", "VerbForm": "Fin"},
                    "extra_tags": [],
                }
            ],
        }
    ]


def test_search_cor_lemma_returns_paradigm_forms(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-lemma/49032", params={"limit": 1000})

    assert response.status_code == 200
    assert [item["form"] for item in response.json()["variants"]] == ["lærer", "lærere"]


def test_search_cor_form_works_when_nlp_is_unavailable(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)

    def failing_nlp_factory(_settings):
        raise RuntimeError("NLP startup failed")

    app = create_app(build_test_settings(db_path, cor_local_db_path=cor_db_path), nlp_adapter_factory=failing_nlp_factory)
    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "lærer", "include_translations": "false"})

    assert response.status_code == 200
    assert len(response.json()["groups"]) == 2


def test_search_cor_form_returns_azure_error_when_translations_requested_without_service(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    cor_db_path = tmp_path / "cor.sqlite"
    apply_migrations(db_path)
    seed_cor_local_db(cor_db_path)
    app = create_app(
        build_test_settings(db_path, cor_local_db_path=cor_db_path),
        nlp_adapter_factory=stub_nlp_adapter_factory,
    )

    with TestClient(app) as client:
        response = client.get("/api/wordbank/search/cor-form", params={"form": "lærer"})

    assert response.status_code == 503
    assert response.json()["detail"] == "Azure translation is unavailable."

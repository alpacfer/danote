from time import perf_counter

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.migrations import apply_migrations
from app.db.repositories import WordbankRepository
from app.main import create_app


def _test_settings(db_path) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="da_dacy_small_trf-0.2.0",
        translation_enabled=False,
    )


def test_wordbank_routes_meet_smoke_latency_budget(tmp_path, stub_nlp_adapter_factory) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)
    for index in range(2_000):
        lemma = f"lemma{index:04d}"
        lexeme_id, _ = repository.insert_or_load_lexeme(
            stored_lemma=lemma,
            translation=f"translation {index:04d}",
            provider="stub",
            pos_tag="NOUN",
            morphology="Number=Sing",
        )
        for variation in range(3):
            repository.insert_or_update_surface_form(
                lexeme_id=lexeme_id,
                form=lemma if variation == 0 else f"{lemma}-form{variation}",
                translation=None,
                provider="stub",
                pos_tag="NOUN",
                morphology="Number=Sing",
            )
    app = create_app(_test_settings(db_path), nlp_adapter_factory=stub_nlp_adapter_factory)

    with TestClient(app) as client:
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogen", "lemma_candidate": "bog"})
        client.post("/api/wordbank/lexemes", json={"surface_token": "bogens", "lemma_candidate": "bog"})

        budgets_ms = {
            "/api/wordbank/lemmas": 400.0,
            "/api/wordbank/lemmas/bog": 400.0,
            "/api/wordbank/search?query=bog&limit=8": 200.0,
            "/api/wordbank/resolve-query": 700.0,
        }

        started_at = perf_counter()
        lemmas_response = client.get("/api/wordbank/lemmas")
        lemmas_duration_ms = (perf_counter() - started_at) * 1000
        assert lemmas_response.status_code == 200
        assert lemmas_duration_ms < budgets_ms["/api/wordbank/lemmas"]

        started_at = perf_counter()
        details_response = client.get("/api/wordbank/lemmas/bog")
        details_duration_ms = (perf_counter() - started_at) * 1000
        assert details_response.status_code == 200
        assert details_duration_ms < budgets_ms["/api/wordbank/lemmas/bog"]

        started_at = perf_counter()
        search_response = client.get("/api/wordbank/search", params={"query": "bog", "limit": 8})
        search_duration_ms = (perf_counter() - started_at) * 1000
        assert search_response.status_code == 200
        assert search_duration_ms < budgets_ms["/api/wordbank/search?query=bog&limit=8"]

        started_at = perf_counter()
        resolve_response = client.post(
            "/api/wordbank/resolve-query",
            json={
                "query_text": "bogen",
                "include_translations": False,
                "include_language_detection": False,
            },
        )
        resolve_duration_ms = (perf_counter() - started_at) * 1000
        assert resolve_response.status_code == 200
        assert resolve_duration_ms < budgets_ms["/api/wordbank/resolve-query"]

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.app_state import BackendServices
from app.core.config import Settings
from app.services.user_service_resolver import UserServiceResolver


class _FakeRepo:
    def __init__(self, mapping: dict[int, dict[str, str]]) -> None:
        self._mapping = mapping
        self.calls: list[int] = []

    def get_all_plaintext(self, *, user_id: int) -> dict[str, str]:
        self.calls.append(user_id)
        return dict(self._mapping.get(user_id, {}))


@dataclass
class _FakeService:
    label: str
    api_key: str = ""


def _settings(**overrides: Any) -> Settings:
    base: dict[str, Any] = {
        "environment": "test",
        "app_name": "danote-backend-test",
        "host": "127.0.0.1",
        "port": 8001,
        "db_path": Path("/tmp/danote-resolver-test.sqlite3"),
        "nlp_model": "stub-model",
        "translation_provider": "deepl",
        "translation_deepl_api_key": "host-deepl",
        "gemini_api_key": "host-gemini",
        "tts_provider": "azure",
        "tts_enabled": True,
        "tts_azure_api_key": "host-tts",
        "tts_azure_region": "westeurope",
        "word_verification_enabled": True,
    }
    base.update(overrides)
    return Settings(**base)


def _host_services() -> BackendServices:
    return BackendServices(
        translation_service=_FakeService(label="host-translation"),
        gemini_word_translation_service=_FakeService(label="host-gemini-word"),
        gemini_related_words_service=_FakeService(label="host-gemini-related"),
        en_gemini_translation_service=_FakeService(label="host-en-gemini"),
        word_verification_service=_FakeService(label="host-word-verify"),
        sentence_verification_service=_FakeService(label="host-sentence-verify"),
        tts_service=_FakeService(label="host-tts"),
        nlp_adapter=object(),
        cor_lexicon_service=object(),
        cor_local_lexicon_service=object(),
        en_local_lexicon_service=object(),
    )


def test_resolve_returns_fallback_when_repo_missing() -> None:
    settings = _settings()
    fallback = _host_services()
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=None,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=42)

    assert result is fallback


def test_resolve_returns_fallback_when_user_has_no_stored_keys() -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=42)

    assert result is fallback
    assert repo.calls == [42]


def test_resolve_swaps_gemini_services_when_user_has_gemini_key() -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({7: {"gemini": "user-gemini-key"}})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=7)

    # All five gemini-backed services must be swapped to user-keyed instances.
    assert result.gemini_word_translation_service is not fallback.gemini_word_translation_service
    assert result.gemini_related_words_service is not fallback.gemini_related_words_service
    assert result.en_gemini_translation_service is not fallback.en_gemini_translation_service
    assert result.word_verification_service is not fallback.word_verification_service
    assert result.sentence_verification_service is not fallback.sentence_verification_service
    # Non-gemini providers stay on host fallback.
    assert result.translation_service is fallback.translation_service
    assert result.tts_service is fallback.tts_service
    # Verify the user key is actually carried into one of the built adapters.
    assert getattr(result.gemini_word_translation_service, "api_key", None) == "user-gemini-key"


def test_resolve_swaps_deepl_when_host_uses_deepl_and_user_has_deepl_key() -> None:
    settings = _settings(translation_provider="deepl")
    fallback = _host_services()
    repo = _FakeRepo({3: {"deepl": "user-deepl"}})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=3)

    assert result.translation_service is not fallback.translation_service
    assert getattr(result.translation_service, "api_key", None) == "user-deepl"


def test_resolve_ignores_azure_key_when_host_uses_deepl() -> None:
    settings = _settings(translation_provider="deepl")
    fallback = _host_services()
    repo = _FakeRepo({3: {"azure_translation": "user-azure"}})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=3)

    # User's azure key is irrelevant because host runs DeepL — fallback to host.
    assert result.translation_service is fallback.translation_service


def test_resolve_swaps_azure_tts_when_user_provides_tts_key() -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({9: {"azure_tts": "user-tts"}})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=9)

    assert result.tts_service is not fallback.tts_service
    assert getattr(result.tts_service, "api_key", None) == "user-tts"


def test_resolve_returns_fallback_on_repo_failure() -> None:
    class _BoomRepo:
        def get_all_plaintext(self, *, user_id: int) -> dict[str, str]:
            raise RuntimeError("decrypt failed")

    settings = _settings()
    fallback = _host_services()
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=_BoomRepo(),
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=1)

    assert result is fallback


def test_resolve_caches_services_across_requests() -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({7: {"gemini": "user-gemini-key"}})
    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    # First resolve: should build new services and query repo
    result1 = resolver.resolve(user_id=7)
    assert len(repo.calls) == 1

    # Second resolve: should return cached instance and NOT query repo
    result2 = resolver.resolve(user_id=7)
    assert result2 is result1
    assert len(repo.calls) == 1


def test_clear_cache_for_user_invalidates_and_closes(monkeypatch) -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({7: {"gemini": "user-gemini-key"}})

    # Create dummy closable service
    class _ClosableFakeService:
        def __init__(self, *args, **kwargs):
            self.closed = False
        def close(self):
            self.closed = True

    dummy_service = _ClosableFakeService()

    # Monkeypatch builder to return our dummy closable service
    from app.services import user_service_builders
    monkeypatch.setattr(user_service_builders, "build_gemini_word_translation_service", lambda **kw: dummy_service)

    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    result = resolver.resolve(user_id=7)
    assert result.gemini_word_translation_service is dummy_service
    assert not dummy_service.closed

    # Clear cache for user: should close user service
    resolver.clear_cache_for_user(7)
    assert dummy_service.closed

    # Next resolve should fetch from repo again
    result3 = resolver.resolve(user_id=7)
    assert len(repo.calls) == 2


def test_close_resolver_closes_all_cached_services(monkeypatch) -> None:
    settings = _settings()
    fallback = _host_services()
    repo = _FakeRepo({7: {"gemini": "user-gemini-key"}})

    class _ClosableFakeService:
        def __init__(self, *args, **kwargs):
            self.closed = False
        def close(self):
            self.closed = True

    dummy_service = _ClosableFakeService()

    from app.services import user_service_builders
    monkeypatch.setattr(user_service_builders, "build_gemini_word_translation_service", lambda **kw: dummy_service)

    resolver = UserServiceResolver(
        settings=settings,
        user_api_keys_repository=repo,
        fallback_services=fallback,
    )

    resolver.resolve(user_id=7)
    assert not dummy_service.closed

    resolver.close()
    assert dummy_service.closed

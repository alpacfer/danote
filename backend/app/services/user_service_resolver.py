from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field, replace

from app.core.app_state import BackendServices
from app.core.config import Settings
from app.db.repositories.user_api_keys import UserApiKeysRepository
from app.services import user_service_builders as builders

logger = logging.getLogger(__name__)


_GEMINI_PROVIDER = "gemini"
_DEEPL_PROVIDER = "deepl"
_AZURE_TRANSLATION_PROVIDER = "azure_translation"
_AZURE_TTS_PROVIDER = "azure_tts"


@dataclass(frozen=True)
class UserServiceResolver:
    """Resolve a per-request `BackendServices` bundle using the calling user's stored API keys.

    For each provider where the user has stored a key, a fresh adapter is built
    with that key. For providers without a user key, the host-level singleton is
    reused (host pays). NLP, COR, and local lexicons don't depend on user keys
    and are always passed through.
    """

    settings: Settings
    user_api_keys_repository: UserApiKeysRepository | None
    fallback_services: BackendServices

    _cache: dict[int, BackendServices] = field(
        default_factory=dict, init=False, compare=False, hash=False
    )
    _lock: threading.Lock = field(
        default_factory=threading.Lock, init=False, compare=False, hash=False
    )

    def resolve(self, user_id: int) -> BackendServices:
        with self._lock:
            cached = self._cache.get(user_id)
            if cached is not None:
                return cached

        repo = self.user_api_keys_repository
        if repo is None:
            return self.fallback_services

        try:
            user_keys = repo.get_all_plaintext(user_id=user_id)
        except Exception:
            logger.exception("user_service_resolver_lookup_failed", extra={"user_id": user_id})
            return self.fallback_services

        if not user_keys:
            return self.fallback_services

        built = self._build(user_keys)

        with self._lock:
            old = self._cache.get(user_id)
            self._cache[user_id] = built

        if old is not None:
            self._close_user_services(old)

        return built

    def clear_cache_for_user(self, user_id: int) -> None:
        with self._lock:
            old = self._cache.pop(user_id, None)
        if old is not None:
            self._close_user_services(old)

    def close(self) -> None:
        with self._lock:
            cached_entries = list(self._cache.values())
            self._cache.clear()
        for services in cached_entries:
            self._close_user_services(services)

    def _close_user_services(self, services: BackendServices) -> None:
        for field_name in (
            "translation_service",
            "gemini_word_translation_service",
            "gemini_related_words_service",
            "en_gemini_translation_service",
            "word_verification_service",
            "sentence_verification_service",
            "tts_service",
        ):
            user_service = getattr(services, field_name, None)
            fallback_service = getattr(self.fallback_services, field_name, None)
            if user_service is not None and user_service is not fallback_service:
                close = getattr(user_service, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        logger.exception(
                            "failed_to_close_user_service", extra={"field": field_name}
                        )

    def _build(self, user_keys: dict[str, str]) -> BackendServices:
        settings = self.settings
        fallback = self.fallback_services

        translation_service = fallback.translation_service
        host_translation_provider = settings.translation_provider.strip().lower()
        if host_translation_provider == "deepl":
            user_translation_key = user_keys.get(_DEEPL_PROVIDER)
            if user_translation_key:
                built = builders.build_translation_service(settings=settings, api_key=user_translation_key)
                if built is not None:
                    translation_service = built
        elif host_translation_provider == "azure":
            user_translation_key = user_keys.get(_AZURE_TRANSLATION_PROVIDER)
            if user_translation_key:
                built = builders.build_translation_service(settings=settings, api_key=user_translation_key)
                if built is not None:
                    translation_service = built

        gemini_word_translation_service = fallback.gemini_word_translation_service
        gemini_related_words_service = fallback.gemini_related_words_service
        en_gemini_translation_service = fallback.en_gemini_translation_service
        word_verification_service = fallback.word_verification_service
        sentence_verification_service = fallback.sentence_verification_service

        user_gemini_key = user_keys.get(_GEMINI_PROVIDER)
        if user_gemini_key:
            built_word = builders.build_gemini_word_translation_service(
                settings=settings, api_key=user_gemini_key
            )
            if built_word is not None:
                gemini_word_translation_service = built_word

            built_related = builders.build_gemini_related_words_service(
                settings=settings, api_key=user_gemini_key
            )
            if built_related is not None:
                gemini_related_words_service = built_related

            built_en = builders.build_en_gemini_translation_service(
                settings=settings, api_key=user_gemini_key
            )
            if built_en is not None:
                en_gemini_translation_service = built_en

            built_word_verification = builders.build_word_verification_service(
                settings=settings, api_key=user_gemini_key
            )
            if built_word_verification is not None:
                word_verification_service = built_word_verification

            built_sentence_verification = builders.build_sentence_verification_service(
                settings=settings, api_key=user_gemini_key
            )
            if built_sentence_verification is not None:
                sentence_verification_service = built_sentence_verification

        tts_service = fallback.tts_service
        user_tts_key = user_keys.get(_AZURE_TTS_PROVIDER)
        if user_tts_key:
            built_tts = builders.build_tts_service(settings=settings, api_key=user_tts_key)
            if built_tts is not None:
                tts_service = built_tts

        return replace(
            fallback,
            translation_service=translation_service,
            gemini_word_translation_service=gemini_word_translation_service,
            gemini_related_words_service=gemini_related_words_service,
            en_gemini_translation_service=en_gemini_translation_service,
            word_verification_service=word_verification_service,
            sentence_verification_service=sentence_verification_service,
            tts_service=tts_service,
        )

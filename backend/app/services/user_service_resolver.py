from __future__ import annotations

import logging
from dataclasses import dataclass, replace

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

    def resolve(self, user_id: int) -> BackendServices:
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

        return self._build(user_keys)

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

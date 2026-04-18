from __future__ import annotations

from collections.abc import Callable
import logging
from pathlib import Path

import httpx

from app.api.schemas.v1.wordbank import (
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GenerateReverseTranslationResponse,
    GenerateTranslationResponse,
)
from app.db.migrations import get_connection
from app.services.cor_local import CORLocalLexiconService
from app.services.gemini_translation import (
    AlternativeTranslationsInput,
    ContextualWordTranslationInput,
    GeminiTranslationError,
    GeminiWordTranslationService,
    MeaningSectionCandidateInput,
    MeaningSectionSelectionInput,
)
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService
from app.services.use_cases.wordbank.collaborators import translation_lookup_ops
from app.services.use_cases.wordbank.collaborators import translation_meaning_selection
from app.services.use_cases.wordbank.collaborators import translation_models
from app.services.use_cases.wordbank.collaborators import translation_sentence_ops
from app.services.use_cases.wordbank.collaborators.translation_contextual import (
    build_contextual_input,
)
from app.services.use_cases.wordbank.collaborators.translation_language_detection import (
    detect_word_language as detect_word_language_with_fallbacks,
)
from app.services.use_cases.wordbank.collaborators.translation_models import (
    AlternativeTranslationsLookupResult,
    TranslationLookupResult,
)
from app.services.use_cases.wordbank.collaborators.translation_provider_fallback import (
    contextual_provider_name as resolve_contextual_provider_name,
    provider_name as resolve_provider_name,
)
from app.services.use_cases.wordbank.collaborators.translation_sentence_text import (
    align_sentence_translation_capitalization,
    normalize_sentence_text,
    normalize_sentence_translation_value,
)
from app.services.translation import TranslationError, TranslationService
from app.services.use_cases.wordbank.collaborators.translation_failures import (
    ProviderCallResult,
    ProviderFailureReason,
)
from app.services.use_cases.wordbank.collaborators.translation_helpers import (
    best_cor_local_entry,
    best_cor_local_entry_with_gloss,
    contextual_provider_name,
    is_likely_english_word,
    log_provider_failure,
    normalize_comparable,
    normalize_translation_value,
    not_configured_result,
    provider_failure_result,
    provider_name,
)
from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    WordTranslationFrame,
    build_word_translation_frame,
    cleanup_framed_word_translation,
    cor_local_word_translation_frame,
)


logger = logging.getLogger(__name__)
class TranslationCollaborator:
    """Handles DA↔EN translation, language detection, and related DB writes."""

    def __init__(
        self,
        translation_service: TranslationService | None,
        gemini_word_translation_service: GeminiWordTranslationService | None,
        cor_local_lexicon_service: CORLocalLexiconService | None,
        db_path: Path,
    ) -> None:
        self._translation_service = translation_service
        self._gemini_word_translation_service = gemini_word_translation_service
        self._cor_local_lexicon_service = cor_local_lexicon_service
        self._db_path = db_path
        self._logger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_translation(
        self, surface_token: str, lemma_candidate: str | None
    ) -> GenerateTranslationResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not normalized_surface:
            raise ValueError("surface_token or lemma_candidate is required")

        translation_result = self.lookup_word_translation(
            normalized_surface,
            normalized_lemma or normalized_surface,
        )
        english_translation = translation_result.translation

        return GenerateTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_word=normalized_surface,
            lemma=stored_lemma,
            english_translation=english_translation,
        )

    def generate_phrase_translation(self, source_text: str) -> GeneratePhraseTranslationResponse:
        return translation_sentence_ops.generate_phrase_translation(self, source_text)

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        return translation_sentence_ops.generate_reverse_translation(self, source_word)

    def detect_word_language(
        self,
        source_word: str,
        *,
        cor_entries_lookup: Callable[[str], list] | None = None,
    ) -> DetectWordLanguageResponse:
        return translation_sentence_ops.detect_word_language(
            self,
            source_word,
            cor_entries_lookup=cor_entries_lookup,
        )

    def lookup_translation(self, source_word: str) -> str | None:
        return self.lookup_translation_result(source_word).value

    def _lookup_phrase_translation(self, source_text: str) -> str | None:
        return translation_sentence_ops.lookup_phrase_translation(self, source_text)

    def lookup_translation_result(self, source_word: str) -> ProviderCallResult:
        if self._translation_service is None:
            return not_configured_result(provider=provider_name(self._translation_service), operation="translate_da_to_en")
        try:
            translated = self._translation_service.translate_da_to_en(source_word)
            return ProviderCallResult(value=normalize_translation_value(translated))
        except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.TIMEOUT,
                retryable=True,
                exc=exc,
            )
        except (httpx.HTTPStatusError, PermissionError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.AUTH,
                retryable=False,
                exc=exc,
            )
        except (httpx.HTTPError, ConnectionError, RuntimeError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.PROVIDER,
                retryable=True,
                exc=exc,
            )

    def lookup_translation_strict(self, source_word: str) -> str | None:
        if self._translation_service is None:
            raise RuntimeError("Azure translation is unavailable.")
        try:
            translated = self._translation_service.translate_da_to_en(source_word)
        except (TranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError, RuntimeError) as exc:
            raise RuntimeError("Azure translation is unavailable.") from exc
        return normalize_translation_value(translated)

    def lookup_translation_batch_strict(self, texts: list[str]) -> dict[str, str | None]:
        if self._translation_service is None:
            raise RuntimeError("Azure translation is unavailable.")
        unique = list(dict.fromkeys(texts))
        if not unique:
            return {}
        try:
            raw_results = self._translation_service.translate_da_to_en_batch(unique)
        except (TranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError, RuntimeError) as exc:
            raise RuntimeError("Azure translation is unavailable.") from exc
        return {
            text: normalize_translation_value(result)
            for text, result in zip(unique, raw_results, strict=False)
        }

    def lookup_word_translation(self, source_word: str, lemma: str | None = None) -> TranslationLookupResult:
        return translation_lookup_ops.lookup_word_translation(self, source_word, lemma)

    def lookup_contextual_word_translation(
        self,
        *,
        surface_form: str,
        lemma: str,
        pos_tag: str | None = None,
        morphology: str | None = None,
        gloss: str | None = None,
        lemma_translation_hint: str | None = None,
        gloss_translation_hint: str | None = None,
        cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] | None = None,
    ) -> TranslationLookupResult:
        return translation_lookup_ops.lookup_contextual_word_translation(
            self,
            surface_form=surface_form,
            lemma=lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=gloss,
            lemma_translation_hint=lemma_translation_hint,
            gloss_translation_hint=gloss_translation_hint,
            cache=cache,
        )

    def lookup_framed_word_translation(
        self,
        frame: WordTranslationFrame,
        *,
        strict: bool = False,
    ) -> TranslationLookupResult:
        translated = self._lookup_framed_word_translation_value(frame, strict=strict)
        return TranslationLookupResult(
            translation=translated,
            provider=provider_name(self._translation_service) if translated else None,
        )

    def cleanup_framed_word_translation(
        self,
        frame: WordTranslationFrame,
        translated: str | None,
    ) -> str | None:
        return cleanup_framed_word_translation(frame, translated)

    def build_word_translation_frame(
        self,
        *,
        lemma: str,
        pos_tag: str | None = None,
        pos_code: str | None = None,
        gram_or_function: str | None = None,
        morphology: str | None = None,
    ) -> WordTranslationFrame:
        return build_word_translation_frame(
            lemma=lemma,
            pos_tag=pos_tag,
            pos_code=pos_code,
            gram_or_function=gram_or_function,
            morphology=morphology,
        )

    def contextual_translation_cache_key(
        self,
        payload: ContextualWordTranslationInput,
    ) -> tuple[str, str, str | None, str | None, str | None, str | None, str | None]:
        return (
            payload.surface_form,
            payload.lemma,
            payload.pos_tag,
            payload.morphology,
            payload.gloss,
            payload.lemma_translation_hint,
            payload.gloss_translation_hint,
        )

    def batch_lookup_contextual_word_translations(
        self,
        payloads: list[ContextualWordTranslationInput],
        *,
        cache: dict[tuple[str, str, str | None, str | None, str | None, str | None, str | None], str | None]
        | None = None,
    ) -> list[TranslationLookupResult]:
        return translation_lookup_ops.batch_lookup_contextual_word_translations(
            self,
            payloads,
            cache=cache,
        )

    def lookup_contextual_word_translation_from_payload(
        self,
        payload: ContextualWordTranslationInput,
        *,
        cache: dict[tuple[str, str, str | None, str | None, str | None, str | None, str | None], str | None]
        | None = None,
    ) -> TranslationLookupResult:
        return translation_lookup_ops.lookup_contextual_word_translation_from_payload(
            self,
            payload,
            cache=cache,
        )

    def find_alternative_translations(
        self,
        *,
        surface_form: str,
        lemma: str,
        pos_tag: str | None,
        morphology: str | None,
        gloss: str | None,
        current_translation: str | None,
        existing_additional_translations: list[str],
    ) -> AlternativeTranslationsLookupResult:
        return translation_meaning_selection.find_alternative_translations(
            self,
            surface_form=surface_form,
            lemma=lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=gloss,
            current_translation=current_translation,
            existing_additional_translations=existing_additional_translations,
        )

    def select_meaning_section(
        self,
        *,
        surface_form: str,
        lemma: str,
        pos_tag: str | None,
        morphology: str | None,
        gloss: str | None,
        english_translation: str | None,
        sentence_context: str | None = None,
        meaning_candidates: list[object],
    ) -> int | None:
        return translation_meaning_selection.select_meaning_section(
            self,
            surface_form=surface_form,
            lemma=lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=gloss,
            english_translation=english_translation,
            sentence_context=sentence_context,
            meaning_candidates=meaning_candidates,
        )

    def select_meaning_sections_batch(
        self,
        payloads: list[dict[str, object]],
    ) -> list[int | None]:
        return translation_meaning_selection.select_meaning_sections_batch(self, payloads)

    def provider_name(self) -> str:
        return resolve_provider_name(self._translation_service)

    def contextual_provider_name(self) -> str:
        return resolve_contextual_provider_name(self._gemini_word_translation_service)

    def normalize_comparable(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def is_likely_english_word(self, value: str) -> bool:
        normalized = value.strip().lower()
        if not normalized or " " in normalized:
            return False
        if any(char in normalized for char in ("æ", "ø", "å")):
            return False
        allowed = set("abcdefghijklmnopqrstuvwxyz'-")
        if any(char not in allowed for char in normalized):
            return False
        return any(char in "aeiouy" for char in normalized)

    def lookup_reverse_translation(self, source_word: str) -> str | None:
        return self.lookup_reverse_translation_result(source_word).value

    def lookup_reverse_translation_result(self, source_word: str) -> ProviderCallResult:
        return self._lookup_reverse_translation(source_word)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _lookup_reverse_translation(self, source_word: str) -> ProviderCallResult:
        return translation_sentence_ops.lookup_reverse_translation_result(self, source_word)

    def _lookup_framed_word_translation_value(
        self,
        frame: WordTranslationFrame,
        *,
        strict: bool,
    ) -> str | None:
        if strict:
            translated = self.lookup_translation_strict(frame.text)
        else:
            translated = self.lookup_translation(frame.text)
        return cleanup_framed_word_translation(frame, translated)

    def _lookup_detected_source_language(self, source_word: str) -> str | None:
        result = self._lookup_detected_source_language_result(source_word)
        if not isinstance(result.value, str):
            return None
        return result.value

    def _lookup_detected_source_language_result(self, source_word: str) -> ProviderCallResult:
        return translation_sentence_ops.lookup_detected_source_language_result(self, source_word)

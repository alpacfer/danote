from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
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
from app.services.use_cases.wordbank.collaborators.translation_contextual import (
    build_contextual_input,
)
from app.services.use_cases.wordbank.collaborators.translation_language_detection import (
    detect_word_language as detect_word_language_with_fallbacks,
)
from app.services.use_cases.wordbank.collaborators.translation_provider_fallback import (
    contextual_provider_name as resolve_contextual_provider_name,
    provider_name as resolve_provider_name,
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


def _normalize_sentence_text(source_text: str) -> str:
    return " ".join(source_text.strip().split())


def _normalize_sentence_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _align_sentence_translation_capitalization(
    source_text: str,
    english_translation: str | None,
) -> str | None:
    if not english_translation:
        return None

    source_index = next((idx for idx, char in enumerate(source_text) if char.isalpha()), None)
    translation_index = next((idx for idx, char in enumerate(english_translation) if char.isalpha()), None)
    if translation_index is None:
        return english_translation

    translation_char = english_translation[translation_index]
    if source_index is None or source_text[source_index].islower():
        if translation_char.islower():
            return (
                english_translation[:translation_index]
                + translation_char.upper()
                + english_translation[translation_index + 1:]
            )
        return english_translation

    if source_text[source_index].isupper() and translation_char.islower():
        return (
            english_translation[:translation_index]
            + translation_char.upper()
            + english_translation[translation_index + 1:]
        )
    return english_translation


@dataclass(frozen=True, slots=True)
class TranslationLookupResult:
    translation: str | None
    provider: str | None


@dataclass(frozen=True, slots=True)
class AlternativeTranslationsLookupResult:
    primary_translation: str | None
    alternative_translations: list[str]
    provider: str | None


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
        normalized_source_text = normalize_token(source_text)
        display_source_text = _normalize_sentence_text(source_text)
        if not normalized_source_text or not display_source_text:
            raise ValueError("source_text is required")

        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT english_translation
                FROM phrase_translations
                WHERE source_phrase = ?
                LIMIT 1
                """,
                (normalized_source_text,),
            ).fetchone()

            if existing is not None:
                cached_translation = _align_sentence_translation_capitalization(
                    display_source_text,
                    _normalize_sentence_translation_value(existing["english_translation"]),
                )
                return GeneratePhraseTranslationResponse(
                    status="cached" if cached_translation else "unavailable",
                    source_text=display_source_text,
                    english_translation=cached_translation,
                )

            english_translation = _align_sentence_translation_capitalization(
                display_source_text,
                self._lookup_phrase_translation(display_source_text),
            )
            provider = provider_name(self._translation_service)
            conn.execute(
                """
                INSERT INTO phrase_translations (
                    source_phrase,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?)
                """,
                (
                    normalized_source_text,
                    english_translation,
                    provider if english_translation else None,
                ),
            )

        return GeneratePhraseTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_text=display_source_text,
            english_translation=english_translation,
        )

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        normalized_source = normalize_token(source_word)
        if not normalized_source:
            raise ValueError("source_word is required")
        danish_translation_raw = self._lookup_reverse_translation(normalized_source).value
        danish_translation = (
            normalize_token(danish_translation_raw) if danish_translation_raw else None
        )
        return GenerateReverseTranslationResponse(
            status="generated" if danish_translation else "unavailable",
            source_word=normalized_source,
            danish_translation=danish_translation,
        )

    def detect_word_language(
        self,
        source_word: str,
        *,
        cor_entries_lookup: Callable[[str], list] | None = None,
    ) -> DetectWordLanguageResponse:
        """Detect whether source_word is Danish, English, or ambiguous.

        cor_entries_lookup: optional callable(normalized_token) -> list[COREntry].
        When provided, a non-empty result signals the word is Danish.
        """
        return detect_word_language_with_fallbacks(
            source_word,
            detect_source_language=self._lookup_detected_source_language,
            cor_entries_lookup=cor_entries_lookup,
        )

    def lookup_translation(self, source_word: str) -> str | None:
        return self.lookup_translation_result(source_word).value

    def _lookup_phrase_translation(self, source_text: str) -> str | None:
        if self._translation_service is None:
            return None
        try:
            translated = self._translation_service.translate_da_to_en(source_text)
            if translated is None:
                normalized_source_text = normalize_token(source_text)
                if normalized_source_text and normalized_source_text != source_text:
                    translated = self._translation_service.translate_da_to_en(normalized_source_text)
            return _normalize_sentence_translation_value(translated)
        except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
            log_provider_failure(
                logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.TIMEOUT,
                retryable=True,
                exc=exc,
            )
            return None
        except (httpx.HTTPStatusError, PermissionError) as exc:
            log_provider_failure(
                logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.HTTP,
                retryable=False,
                exc=exc,
            )
            return None
        except Exception as exc:
            log_provider_failure(
                logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_da_to_en",
                reason=ProviderFailureReason.UNKNOWN,
                retryable=False,
                exc=exc,
            )
            return None

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
        normalized_source = normalize_token(source_word)
        normalized_lemma = normalize_token(lemma or "") or normalized_source
        contextual = self.lookup_contextual_word_translation(
            surface_form=normalized_source,
            lemma=normalized_lemma,
        )
        if contextual.translation:
            return contextual

        cor_entry = best_cor_local_entry(
            self._cor_local_lexicon_service,
            form=normalized_source,
            lemma=normalized_lemma,
            preferred_pos_tag=None,
        )
        if cor_entry is not None:
            framed_translation = self.lookup_framed_word_translation(
                cor_local_word_translation_frame(cor_entry)
            )
            if framed_translation.translation:
                if (
                    " " not in normalized_source
                    and normalize_comparable(framed_translation.translation)
                    == normalize_comparable(normalized_source)
                ):
                    return TranslationLookupResult(translation=None, provider=None)
                return framed_translation

        translated = self.lookup_translation(normalized_source)
        if (
            translated
            and " " not in normalized_source
            and normalize_comparable(translated) == normalize_comparable(normalized_source)
        ):
            return TranslationLookupResult(translation=None, provider=None)
        return TranslationLookupResult(
            translation=translated,
            provider=provider_name(self._translation_service) if translated else None,
        )

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
        normalized_surface = normalize_token(surface_form)
        normalized_lemma = normalize_token(lemma)
        normalized_gloss = normalize_token(gloss or "")
        if not normalized_surface or not normalized_lemma:
            return TranslationLookupResult(translation=None, provider=None)

        context_entry = build_contextual_input(
            surface_form=normalized_surface,
            lemma=normalized_lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=normalized_gloss,
            lemma_translation_hint=lemma_translation_hint,
            gloss_translation_hint=gloss_translation_hint,
            best_cor_local_entry_with_gloss=lambda **kwargs: best_cor_local_entry_with_gloss(
                self._cor_local_lexicon_service,
                **kwargs,
            ),
        )

        if self._gemini_word_translation_service is None:
            return TranslationLookupResult(translation=None, provider=None)

        cache_key = (
            context_entry.surface_form,
            context_entry.lemma,
            context_entry.pos_tag,
            context_entry.morphology,
            context_entry.gloss,
            context_entry.lemma_translation_hint,
            context_entry.gloss_translation_hint,
        )
        if cache is not None and cache_key in cache:
            return TranslationLookupResult(
                translation=cache[cache_key],
                provider=contextual_provider_name(self._gemini_word_translation_service),
            )

        try:
            translated = self._gemini_word_translation_service.translate_word(context_entry)
            normalized = normalize_translation_value(translated)
        except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
            log_provider_failure(logger=logger,
                provider=contextual_provider_name(self._gemini_word_translation_service),
                operation="translate_word",
                reason=ProviderFailureReason.PROVIDER,
                retryable=False,
                exc=exc,
            )
            normalized = None

        if cache is not None:
            cache[cache_key] = normalized
        return TranslationLookupResult(
            translation=normalized,
            provider=contextual_provider_name(self._gemini_word_translation_service),
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
        if not payloads:
            return []
        if self._gemini_word_translation_service is None:
            return [TranslationLookupResult(translation=None, provider=None) for _ in payloads]

        try:
            translated = self._gemini_word_translation_service.translate_words_batch(payloads)
        except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
            log_provider_failure(logger=logger,
                provider=contextual_provider_name(self._gemini_word_translation_service),
                operation="translate_words_batch",
                reason=ProviderFailureReason.PROVIDER,
                retryable=False,
                exc=exc,
            )
            translated = [None] * len(payloads)

        results: list[TranslationLookupResult] = []
        for index, payload in enumerate(payloads):
            value = translated[index] if index < len(translated) else None
            normalized = normalize_translation_value(value)
            if cache is not None:
                cache[self.contextual_translation_cache_key(payload)] = normalized
            results.append(
                TranslationLookupResult(
                    translation=normalized,
                    provider=contextual_provider_name(self._gemini_word_translation_service),
                )
            )

        return results

    def lookup_contextual_word_translation_from_payload(
        self,
        payload: ContextualWordTranslationInput,
        *,
        cache: dict[tuple[str, str, str | None, str | None, str | None, str | None, str | None], str | None]
        | None = None,
    ) -> TranslationLookupResult:
        if self._gemini_word_translation_service is None:
            return TranslationLookupResult(translation=None, provider=None)
        cache_key = self.contextual_translation_cache_key(payload)
        if cache is not None and cache_key in cache:
            return TranslationLookupResult(
                translation=cache[cache_key],
                provider=contextual_provider_name(self._gemini_word_translation_service),
            )
        try:
            translated = self._gemini_word_translation_service.translate_word(payload)
            normalized = normalize_translation_value(translated)
        except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
            log_provider_failure(logger=logger,
                provider=contextual_provider_name(self._gemini_word_translation_service),
                operation="translate_word",
                reason=ProviderFailureReason.PROVIDER,
                retryable=False,
                exc=exc,
            )
            normalized = None
        if cache is not None:
            cache[cache_key] = normalized
        return TranslationLookupResult(
            translation=normalized,
            provider=contextual_provider_name(self._gemini_word_translation_service),
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
        if self._gemini_word_translation_service is None:
            return AlternativeTranslationsLookupResult(
                primary_translation=None,
                alternative_translations=[],
                provider=None,
            )
        finder = getattr(self._gemini_word_translation_service, "find_alternative_translations", None)
        if not callable(finder):
            return AlternativeTranslationsLookupResult(
                primary_translation=None,
                alternative_translations=[],
                provider=None,
            )

        payload = AlternativeTranslationsInput(
            surface_form=surface_form,
            lemma=lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=normalize_translation_value(gloss),
            current_translation=normalize_translation_value(current_translation),
            existing_additional_translations=[
                normalized
                for value in existing_additional_translations
                if (normalized := normalize_translation_value(value)) is not None
            ],
        )
        try:
            result = finder(payload)
        except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
            log_provider_failure(logger=logger,
                provider=contextual_provider_name(self._gemini_word_translation_service),
                operation="find_alternative_translations",
                reason=ProviderFailureReason.PROVIDER,
                retryable=False,
                exc=exc,
            )
            return AlternativeTranslationsLookupResult(
                primary_translation=None,
                alternative_translations=[],
                provider=contextual_provider_name(self._gemini_word_translation_service),
            )
        return AlternativeTranslationsLookupResult(
            primary_translation=normalize_translation_value(result.primary_translation),
            alternative_translations=[
                normalized
                for value in result.alternative_translations
                if (normalized := normalize_translation_value(value)) is not None
            ],
            provider=contextual_provider_name(self._gemini_word_translation_service),
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
        if self._gemini_word_translation_service is None or not meaning_candidates:
            return None
        selector = getattr(self._gemini_word_translation_service, "select_meaning_section", None)
        if not callable(selector):
            return None

        candidate_payloads: list[MeaningSectionCandidateInput] = []
        valid_ids: set[int] = set()
        for candidate in meaning_candidates:
            candidate_id = getattr(candidate, "id", None)
            if not isinstance(candidate_id, int):
                continue
            valid_ids.add(candidate_id)
            candidate_payloads.append(
                MeaningSectionCandidateInput(
                    id=candidate_id,
                    meaning_key=str(getattr(candidate, "meaning_key", "")),
                    cor_lemma_idx=getattr(candidate, "cor_lemma_idx", None),
                    gloss=normalize_translation_value(getattr(candidate, "gloss", None)),
                    english_translation=normalize_translation_value(
                        getattr(candidate, "english_translation", None)
                    ),
                    pos_tag=getattr(candidate, "pos_tag", None),
                    morphology=getattr(candidate, "morphology", None),
                )
            )
        if not candidate_payloads:
            return None

        payload = MeaningSectionSelectionInput(
            surface_form=surface_form,
            lemma=lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=normalize_translation_value(gloss),
            english_translation=normalize_translation_value(english_translation),
            sentence_context=" ".join(sentence_context.strip().split()) if isinstance(sentence_context, str) and sentence_context.strip() else None,
            meaning_candidates=candidate_payloads,
        )
        try:
            selected = selector(payload)
        except (GeminiTranslationError, httpx.HTTPError, TimeoutError, ValueError, TypeError) as exc:
            log_provider_failure(logger=logger,
                provider=contextual_provider_name(self._gemini_word_translation_service),
                operation="select_meaning_section",
                reason=ProviderFailureReason.PARSE,
                retryable=False,
                exc=exc,
            )
            return None
        if not isinstance(selected, int) or selected not in valid_ids:
            return None
        return selected

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
        if self._translation_service is None:
            return not_configured_result(provider=provider_name(self._translation_service), operation="translate_en_to_da")
        translate_en_to_da = getattr(self._translation_service, "translate_en_to_da", None)
        if not callable(translate_en_to_da):
            return not_configured_result(provider=provider_name(self._translation_service), operation="translate_en_to_da")
        try:
            translated = translate_en_to_da(source_word)
            return ProviderCallResult(value=normalize_translation_value(translated))
        except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_en_to_da",
                reason=ProviderFailureReason.TIMEOUT,
                retryable=True,
                exc=exc,
            )
        except (httpx.HTTPStatusError, PermissionError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_en_to_da",
                reason=ProviderFailureReason.AUTH,
                retryable=False,
                exc=exc,
            )
        except (httpx.HTTPError, ConnectionError, RuntimeError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="translate_en_to_da",
                reason=ProviderFailureReason.PROVIDER,
                retryable=True,
                exc=exc,
            )

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
        if self._translation_service is None:
            return not_configured_result(provider=provider_name(self._translation_service), operation="detect_source_language")
        detect_source_language = getattr(self._translation_service, "detect_source_language", None)
        if not callable(detect_source_language):
            return not_configured_result(provider=provider_name(self._translation_service), operation="detect_source_language")
        try:
            provider_language = detect_source_language(source_word)
        except (TranslationError, httpx.TimeoutException, TimeoutError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="detect_source_language",
                reason=ProviderFailureReason.TIMEOUT,
                retryable=True,
                exc=exc,
            )
        except (httpx.HTTPStatusError, PermissionError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="detect_source_language",
                reason=ProviderFailureReason.AUTH,
                retryable=False,
                exc=exc,
            )
        except (httpx.HTTPError, ConnectionError, ValueError, TypeError, RuntimeError) as exc:
            return provider_failure_result(logger=logger,
                provider=provider_name(self._translation_service),
                operation="detect_source_language",
                reason=ProviderFailureReason.PARSE,
                retryable=False,
                exc=exc,
            )
        if not provider_language:
            return ProviderCallResult(value=None)
        normalized = provider_language.strip().lower()
        if normalized.startswith("en"):
            return ProviderCallResult(value="en")
        if normalized.startswith("da"):
            return ProviderCallResult(value="da")
        return ProviderCallResult(value=None)

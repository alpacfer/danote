from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field

from app.services.gemini_result_cache import GeminiResultCache
from app.services.gemini_sense_discovery import (
    DiscoveredSenseSet,
    SenseDiscoveryInput,
    discover_senses_with_gemini,
)
from app.services.gemini_translation_configs import (
    alternative_translations_response_config,
    batch_meaning_section_selection_response_config,
    batch_non_cor_word_generation_response_config,
    batch_response_config,
    example_sentence_response_config,
    meaning_section_selection_response_config,
    non_cor_variations_response_config,
    non_cor_word_generation_response_config,
    single_response_config,
)
from app.services.gemini_translation_helpers import (
    build_alternative_translations_prompt,
    build_batch_meaning_section_selection_prompt,
    build_batch_non_cor_word_generation_prompt,
    build_batch_translation_prompt,
    build_example_sentence_prompt,
    build_meaning_section_selection_prompt,
    build_non_cor_variations_prompt,
    build_non_cor_word_generation_prompt,
    build_translation_prompt,
    is_retryable_exception,
)
from app.services.gemini_translation_models import (
    AlternativeTranslationsInput,
    AlternativeTranslationsResult,
    ContextualWordTranslationInput,
    ExampleSentenceGenerationInput,
    ExampleSentenceGenerationResult,
    GeminiTranslationError,
    GeminiWordTranslationService,
    MeaningSectionCandidateInput,
    MeaningSectionSelectionInput,
    NonCORVariationCandidate,
    NonCORVariationGenerationInput,
    NonCORVariationGenerationResult,
    NonCORWordGenerationInput,
    NonCORWordGenerationResult,
)
from app.services.gemini_translation_parsing import (
    parse_alternative_translations_payload,
    parse_batch_meaning_section_payload,
    parse_batch_payload,
    parse_example_sentence_payload,
    parse_meaning_section_payload,
    parse_translation,
)

__all__ = ("AlternativeTranslationsInput", "AlternativeTranslationsResult", "BatchContextualWordTranslationRequestItem", "BatchContextualWordTranslationResponse", "BatchContextualWordTranslationResponseItem", "ContextualWordTranslationInput", "ExampleSentenceGenerationInput", "ExampleSentenceGenerationResult", "GeminiFlashLiteWordTranslationService", "GeminiTranslationError", "GeminiWordTranslationService", "MeaningSectionCandidateInput", "MeaningSectionSelectionInput", "NonCORVariationCandidate", "NonCORVariationGenerationInput", "NonCORVariationGenerationResult", "NonCORWordGenerationInput", "NonCORWordGenerationResult")


@dataclass(frozen=True, slots=True)
class BatchContextualWordTranslationRequestItem:
    id: str
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    lemma_translation_hint: str | None = None
    gloss_translation_hint: str | None = None


@dataclass(frozen=True, slots=True)
class BatchContextualWordTranslationResponseItem:
    id: str
    translation: str | None = None


@dataclass(frozen=True, slots=True)
class BatchContextualWordTranslationResponse:
    items: list[BatchContextualWordTranslationResponseItem]


@dataclass
class GeminiFlashLiteWordTranslationService:
    """Gloss-aware Danish word translation backed by Gemini Flash-Lite."""

    api_key: str
    model: str = "gemini-3.1-flash-lite"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    cache: GeminiResultCache | None = None
    provider: str = field(default="gemini_word_translation", init=False)
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        if not normalized_key:
            raise GeminiTranslationError("Gemini API key is required for contextual word translation.")
        if not normalized_model:
            raise GeminiTranslationError("Gemini model is required for contextual word translation.")
        self.api_key = normalized_key
        self.model = normalized_model

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise GeminiTranslationError(
                    "google-genai package is required for Gemini word translation."
                ) from exc
            genai_types = self._genai_types()
            timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    def close(self) -> None:
        if self.cache is not None:
            self.cache.close()
        self._client = None

    def discover_senses(self, payload: SenseDiscoveryInput) -> DiscoveredSenseSet | None:
        return discover_senses_with_gemini(
            payload,
            cache=self.cache,
            generate_content=lambda prompt, config: self._generate_content(prompt, config=config),
            genai_types_factory=self._genai_types,
        )

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None:
        prompt = build_translation_prompt(payload)
        raw = self._generate_text(prompt)
        return self._parse_translation(raw)

    def translate_words_batch(
        self,
        payloads: list[ContextualWordTranslationInput],
    ) -> list[str | None]:
        if not payloads:
            return []
        request_items = [
            BatchContextualWordTranslationRequestItem(
                id=str(index),
                surface_form=payload.surface_form,
                lemma=payload.lemma,
                pos_tag=payload.pos_tag,
                morphology=payload.morphology,
                gloss=payload.gloss,
                lemma_translation_hint=payload.lemma_translation_hint,
                gloss_translation_hint=payload.gloss_translation_hint,
            )
            for index, payload in enumerate(payloads)
        ]
        prompt = build_batch_translation_prompt(request_items)
        response = self._generate_content(
            prompt,
            config=self._batch_response_config(item_count=len(request_items)),
        )
        parsed = self._parse_batch_translations(response, expected_ids=[item.id for item in request_items])
        by_id = {item.id: item.translation for item in parsed.items}
        return [by_id.get(item.id) for item in request_items]

    def select_meaning_section(self, payload: MeaningSectionSelectionInput) -> int | None:
        if not payload.meaning_candidates:
            return None
        prompt = build_meaning_section_selection_prompt(payload)
        response = self._generate_content(
            prompt,
            config=self._meaning_section_selection_response_config(),
        )
        return self._parse_meaning_section_id(response, valid_ids={item.id for item in payload.meaning_candidates})

    def select_meaning_sections_batch(
        self,
        payloads: list[MeaningSectionSelectionInput],
    ) -> list[int | None]:
        if not payloads:
            return []
        request_items: list[dict[str, object]] = []
        expected_ids: list[str] = []
        valid_ids_by_item: dict[str, set[int]] = {}
        for index, payload in enumerate(payloads):
            item_id = str(index)
            expected_ids.append(item_id)
            valid_ids_by_item[item_id] = {item.id for item in payload.meaning_candidates}
            request_items.append(
                {
                    "id": item_id,
                    "word_context": self._meaning_section_context(payload),
                    "candidate_meaning_sections": self._meaning_section_candidates(payload),
                }
            )
        response = self._generate_content(
            build_batch_meaning_section_selection_prompt(request_items),
            config=self._batch_meaning_section_selection_response_config(item_count=len(request_items)),
        )
        parsed = self._parse_batch_meaning_section_ids(
            response,
            expected_ids=expected_ids,
            valid_ids_by_item=valid_ids_by_item,
        )
        return [parsed.get(item_id) for item_id in expected_ids]

    def find_alternative_translations(
        self,
        payload: AlternativeTranslationsInput,
    ) -> AlternativeTranslationsResult:
        prompt = build_alternative_translations_prompt(payload)
        response = self._generate_content(
            prompt,
            config=self._alternative_translations_response_config(),
        )
        return self._parse_alternative_translations(response)

    def generate_example_sentence(
        self,
        payload: ExampleSentenceGenerationInput,
    ) -> ExampleSentenceGenerationResult | None:
        response = self._generate_content(
            build_example_sentence_prompt(payload),
            config=self._example_sentence_response_config(),
        )
        return self._parse_example_sentence(response)

    def generate_non_cor_word_entry(
        self,
        payload: NonCORWordGenerationInput,
    ) -> NonCORWordGenerationResult | None:
        response = self._generate_content(
            build_non_cor_word_generation_prompt(payload),
            config=self._non_cor_word_generation_response_config(),
        )
        return self._parse_non_cor_word_generation(response)

    def generate_non_cor_word_entries_batch(
        self,
        payloads: list[NonCORWordGenerationInput],
    ) -> list[NonCORWordGenerationResult | None]:
        if not payloads:
            return []
        request_items = [
            {
                "id": str(index),
                "surface_form": payload.surface_form,
                "lemma_candidate": payload.lemma_candidate,
                "pos_tag": payload.pos_tag,
                "morphology": payload.morphology,
                "sentence_context": payload.sentence_context,
            }
            for index, payload in enumerate(payloads)
        ]
        response = self._generate_content(
            build_batch_non_cor_word_generation_prompt(request_items),
            config=self._batch_non_cor_word_generation_response_config(item_count=len(request_items)),
        )
        parsed = self._parse_batch_non_cor_word_generation(
            response,
            expected_ids=[item["id"] for item in request_items],
        )
        by_id = {item_id: result for item_id, result in parsed.items()} if parsed else {}
        return [by_id.get(item["id"]) for item in request_items]

    def complete_non_cor_meaning_variations(
        self,
        payload: NonCORVariationGenerationInput,
    ) -> NonCORVariationGenerationResult:
        response = self._generate_content(
            build_non_cor_variations_prompt(payload),
            config=self._non_cor_variations_response_config(),
        )
        return self._parse_non_cor_variations(response)

    def _single_response_config(self) -> object:
        return single_response_config(self._genai_types())

    def _batch_response_config(self, *, item_count: int) -> object:
        return batch_response_config(self._genai_types(), item_count=item_count)

    def _meaning_section_selection_response_config(self) -> object:
        return meaning_section_selection_response_config(self._genai_types())

    def _batch_meaning_section_selection_response_config(self, *, item_count: int) -> object:
        return batch_meaning_section_selection_response_config(self._genai_types(), item_count=item_count)

    def _alternative_translations_response_config(self) -> object:
        return alternative_translations_response_config(self._genai_types())

    def _example_sentence_response_config(self) -> object:
        return example_sentence_response_config(self._genai_types())

    def _non_cor_word_generation_response_config(self) -> object:
        return non_cor_word_generation_response_config(self._genai_types())

    def _batch_non_cor_word_generation_response_config(self, *, item_count: int) -> object:
        return batch_non_cor_word_generation_response_config(self._genai_types(), item_count=item_count)

    def _non_cor_variations_response_config(self) -> object:
        return non_cor_variations_response_config(self._genai_types())

    def _generate_text(self, prompt: str) -> str | None:
        response = self._generate_content(
            prompt,
            config=self._single_response_config(),
        )
        text = getattr(response, "text", None)
        cleaned = text.strip() if isinstance(text, str) else ""
        return cleaned or None

    def _generate_content(self, prompt: str, *, config: object | None = None) -> object:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                return client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
            except Exception as exc:
                if attempt < self.max_retries and self._is_retryable_exception(exc):
                    delay = self.backoff_seconds * (2**attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise GeminiTranslationError(f"Gemini word translation request failed: {exc}") from exc
        raise GeminiTranslationError("Gemini word translation request failed after retries.")

    def _genai_types(self):
        try:
            from google.genai import types as genai_types  # type: ignore import-not-found
        except ImportError as exc:
            raise GeminiTranslationError(
                "google-genai package is required for Gemini word translation."
            ) from exc
        return genai_types

    @staticmethod
    def _is_retryable_exception(exc: Exception) -> bool:
        return is_retryable_exception(
            exc,
            exception_status_code=GeminiFlashLiteWordTranslationService._exception_status_code,
        )

    @staticmethod
    def _exception_status_code(exc: Exception) -> int | None:
        for candidate in (exc, getattr(exc, "response", None), getattr(exc, "cause", None)):
            if candidate is None:
                continue
            status_code = getattr(candidate, "status_code", None)
            if isinstance(status_code, int):
                return status_code
            code = getattr(candidate, "code", None)
            if isinstance(code, int):
                return code
        return None

    def _parse_translation(self, raw: str | None) -> str | None:
        return parse_translation(raw)

    def _parse_batch_translations(
        self,
        response: object,
        *,
        expected_ids: list[str],
    ) -> BatchContextualWordTranslationResponse:
        parsed_payload = getattr(response, "parsed", None)
        batch = self._parse_batch_payload(parsed_payload, expected_ids=expected_ids)
        if batch is not None:
            return batch

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return BatchContextualWordTranslationResponse(items=[])
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return BatchContextualWordTranslationResponse(items=[])
        batch = self._parse_batch_payload(payload, expected_ids=expected_ids)
        if batch is not None:
            return batch
        return BatchContextualWordTranslationResponse(items=[])

    def _parse_batch_payload(
        self,
        payload: object,
        *,
        expected_ids: list[str],
    ) -> BatchContextualWordTranslationResponse | None:
        return parse_batch_payload(payload, expected_ids=expected_ids)

    def _parse_meaning_section_id(self, response: object, *, valid_ids: set[int]) -> int | None:
        parsed_payload = getattr(response, "parsed", None)
        parsed = self._parse_meaning_section_payload(parsed_payload, valid_ids=valid_ids)
        if parsed is not None:
            return parsed

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return None
        return self._parse_meaning_section_payload(payload, valid_ids=valid_ids)

    def _parse_batch_meaning_section_ids(
        self,
        response: object,
        *,
        expected_ids: list[str],
        valid_ids_by_item: dict[str, set[int]],
    ) -> dict[str, int | None]:
        parsed_payload = getattr(response, "parsed", None)
        parsed = self._parse_batch_meaning_section_payload(
            parsed_payload,
            expected_ids=expected_ids,
            valid_ids_by_item=valid_ids_by_item,
        )
        if parsed is not None:
            return parsed

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return {}
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return {}
        parsed = self._parse_batch_meaning_section_payload(
            payload,
            expected_ids=expected_ids,
            valid_ids_by_item=valid_ids_by_item,
        )
        return parsed or {}

    def _parse_meaning_section_payload(self, payload: object, *, valid_ids: set[int]) -> int | None:
        return parse_meaning_section_payload(payload, valid_ids=valid_ids)

    def _parse_batch_meaning_section_payload(
        self,
        payload: object,
        *,
        expected_ids: list[str],
        valid_ids_by_item: dict[str, set[int]],
    ) -> dict[str, int | None] | None:
        return parse_batch_meaning_section_payload(
            payload,
            expected_ids=expected_ids,
            valid_ids_by_item=valid_ids_by_item,
        )

    def _meaning_section_context(self, payload: MeaningSectionSelectionInput) -> dict[str, object]:
        from app.services.gemini_translation_helpers import _meaning_section_context

        return _meaning_section_context(payload)

    def _meaning_section_candidates(self, payload: MeaningSectionSelectionInput) -> list[dict[str, object]]:
        from app.services.gemini_translation_helpers import _meaning_section_candidates

        return _meaning_section_candidates(payload)

    def _parse_alternative_translations(self, response: object) -> AlternativeTranslationsResult:
        parsed_payload = getattr(response, "parsed", None)
        parsed = parse_alternative_translations_payload(parsed_payload)
        if parsed is not None:
            return parsed

        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return AlternativeTranslationsResult()
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return AlternativeTranslationsResult()
        parsed = parse_alternative_translations_payload(payload)
        if parsed is not None:
            return parsed
        return AlternativeTranslationsResult()

    def _parse_example_sentence(self, response: object) -> ExampleSentenceGenerationResult | None:
        parsed_payload = getattr(response, "parsed", None)
        parsed = parse_example_sentence_payload(parsed_payload)
        if parsed is not None:
            return parsed
        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return None
        return parse_example_sentence_payload(payload)

    def _parse_non_cor_word_generation(self, response: object) -> NonCORWordGenerationResult | None:
        from app.services.gemini_translation_helpers import parse_non_cor_word_entry_payload

        parsed_payload = getattr(response, "parsed", None)
        parsed = parse_non_cor_word_entry_payload(parsed_payload)
        if parsed is not None:
            return parsed
        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return None
        return parse_non_cor_word_entry_payload(payload)

    def _parse_batch_non_cor_word_generation(
        self,
        response: object,
        *,
        expected_ids: list[str],
    ) -> dict[str, NonCORWordGenerationResult | None]:
        from app.services.gemini_translation_helpers import parse_non_cor_word_entries_batch_payload

        parsed_payload = getattr(response, "parsed", None)
        parsed = parse_non_cor_word_entries_batch_payload(parsed_payload, expected_ids=expected_ids)
        if parsed is not None:
            return parsed
        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return {}
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return {}
        return parse_non_cor_word_entries_batch_payload(payload, expected_ids=expected_ids) or {}

    def _parse_non_cor_variations(self, response: object) -> NonCORVariationGenerationResult:
        from app.services.gemini_translation_helpers import parse_non_cor_variations_payload

        parsed_payload = getattr(response, "parsed", None)
        parsed = parse_non_cor_variations_payload(parsed_payload)
        if parsed is not None:
            return parsed
        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return NonCORVariationGenerationResult()
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return NonCORVariationGenerationResult()
        return parse_non_cor_variations_payload(payload) or NonCORVariationGenerationResult()

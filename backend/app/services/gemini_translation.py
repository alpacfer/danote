from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
import time
from typing import Protocol


class GeminiTranslationError(RuntimeError):
    """Raised when Gemini word translation cannot be completed."""


@dataclass(frozen=True, slots=True)
class ContextualWordTranslationInput:
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    lemma_translation_hint: str | None = None
    gloss_translation_hint: str | None = None


@dataclass(frozen=True, slots=True)
class MeaningSectionCandidateInput:
    id: int
    meaning_key: str
    cor_lemma_idx: int | None = None
    gloss: str | None = None
    english_translation: str | None = None
    pos_tag: str | None = None
    morphology: str | None = None


@dataclass(frozen=True, slots=True)
class MeaningSectionSelectionInput:
    surface_form: str
    lemma: str
    pos_tag: str | None = None
    morphology: str | None = None
    gloss: str | None = None
    english_translation: str | None = None
    meaning_candidates: list[MeaningSectionCandidateInput] = field(default_factory=list)


class GeminiWordTranslationService(Protocol):
    provider: str

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None: ...
    def translate_words_batch(
        self, payloads: list[ContextualWordTranslationInput]
    ) -> list[str | None]: ...
    def select_meaning_section(self, payload: MeaningSectionSelectionInput) -> int | None: ...


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
    model: str = "gemini-3.1-flash-lite-preview"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
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
        self._client = None

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None:
        prompt = self._translation_prompt(payload)
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
        prompt = self._batch_translation_prompt(request_items)
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
        prompt = self._meaning_section_selection_prompt(payload)
        response = self._generate_content(
            prompt,
            config=self._meaning_section_selection_response_config(),
        )
        return self._parse_meaning_section_id(response, valid_ids={item.id for item in payload.meaning_candidates})

    def _translation_prompt(self, payload: ContextualWordTranslationInput) -> str:
        context = {
            "surface_form_da": payload.surface_form,
            "lemma_da": payload.lemma,
            "pos_tag": payload.pos_tag,
            "morphology": payload.morphology,
            "gloss": payload.gloss,
            "lemma_translation_hint": payload.lemma_translation_hint,
            "gloss_translation_hint": payload.gloss_translation_hint,
        }
        has_dictionary_context = bool(
            payload.gloss
            or payload.pos_tag
            or payload.morphology
            or payload.lemma_translation_hint
            or payload.gloss_translation_hint
        )
        if has_dictionary_context:
            task_instruction = (
                "You translate Danish lemmas into the exact English lemma or short phrase that matches the supplied "
                "dictionary context.\n"
                "Translate lemma_da, and use surface_form_da, morphology, and gloss only for sense disambiguation.\n"
            )
        else:
            task_instruction = (
                "You translate a single Danish lemma into the exact English lemma or short phrase.\n"
                "Translate lemma_da, and use surface_form_da only as optional context.\n"
            )
        return (
            task_instruction
            + "Return JSON only: {\"translation\":\"...\"}\n"
            + "Rules:\n"
            + "- Output only the English translation.\n"
            + "- Translate lemma_da, not surface_form_da.\n"
            + "- Return a lemma-level translation; avoid adding articles/function words unless part of the lemma meaning.\n"
            + "- Treat pos_tag and morphology as hard constraints for sense disambiguation.\n"
            + "- If multiple senses are possible, choose the most common modern English meaning for the given Danish lemma/POS/morphology.\n"
            + "- Avoid false-friend transliterations and niche domain senses unless gloss or hints explicitly require them.\n"
            + "- For verbs, prefer the common infinitive meaning in English (for example, prefer 'to bend'/'to bow' over golf-specific 'to bogey' unless context explicitly indicates golf).\n"
            + "- Do not explain your reasoning.\n"
            + f"Context:\n{json.dumps(context, ensure_ascii=False)}"
        )

    def _batch_translation_prompt(
        self,
        items: list[BatchContextualWordTranslationRequestItem],
    ) -> str:
        return (
            "You translate Danish lemmas into the exact English lemma or short phrase that matches the supplied "
            "dictionary context.\n"
            "For every item, translate lemma and use surface_form, morphology, and gloss only for sense disambiguation.\n"
            "Return JSON only with this exact shape: "
            "{\"items\":[{\"id\":\"0\",\"translation\":\"...\"}]}\n"
            "Rules:\n"
            "- Return exactly one item for every input id.\n"
            "- Copy each id exactly.\n"
            "- Output only the English translation.\n"
            "- Translate lemma, not surface_form.\n"
            "- Return lemma-level translations; avoid adding articles/function words unless part of the lemma meaning.\n"
            "- Treat pos_tag and morphology as hard constraints for sense disambiguation.\n"
            "- If multiple senses are possible, choose the most common modern English meaning for the given Danish lemma/POS/morphology.\n"
            "- Avoid false-friend transliterations and niche domain senses unless gloss or hints explicitly require them.\n"
            "- For verbs, prefer the common infinitive meaning in English (for example, prefer 'to bend'/'to bow' over golf-specific 'to bogey' unless context explicitly indicates golf).\n"
            "- Do not explain your reasoning.\n"
            f"Items:\n{json.dumps([asdict(item) for item in items], ensure_ascii=False)}"
        )

    def _meaning_section_selection_prompt(self, payload: MeaningSectionSelectionInput) -> str:
        context = {
            "surface_form_da": payload.surface_form,
            "lemma_da": payload.lemma,
            "pos_tag": payload.pos_tag,
            "morphology": payload.morphology,
            "gloss": payload.gloss,
            "english_translation": payload.english_translation,
        }
        candidates = [asdict(item) for item in payload.meaning_candidates]
        return (
            "You are assigning a Danish non-verb word to one existing meaning section.\n"
            "Return JSON only: {\"meaning_section_id\": <integer|null>}\n"
            "Rules:\n"
            "- Choose exactly one section id if there is a confident semantic match.\n"
            "- Use gloss, translation, POS, and morphology as hard disambiguation signals.\n"
            "- Return null if no section is a confident match.\n"
            "- Do not explain your reasoning.\n"
            f"Word context:\n{json.dumps(context, ensure_ascii=False)}\n"
            f"Meaning sections:\n{json.dumps(candidates, ensure_ascii=False)}"
        )

    def _single_response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "translation": {
                        "type": "STRING",
                        "nullable": True,
                    },
                },
                "required": ["translation"],
            },
            temperature=0,
            max_output_tokens=64,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _batch_response_config(self, *, item_count: int) -> object:
        genai_types = self._genai_types()
        max_output_tokens = min(2048, max(128, item_count * 48))
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": {"type": "STRING"},
                                "translation": {
                                    "type": "STRING",
                                    "nullable": True,
                                },
                            },
                            "required": ["id", "translation"],
                        },
                    }
                },
                "required": ["items"],
            },
            temperature=0,
            max_output_tokens=max_output_tokens,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _meaning_section_selection_response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "meaning_section_id": {
                        "type": "INTEGER",
                        "nullable": True,
                    },
                },
                "required": ["meaning_section_id"],
            },
            temperature=0,
            max_output_tokens=64,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

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
        # Retry only transient transport/rate-limit failures, not local config/validation errors.
        if isinstance(exc, (ImportError, ModuleNotFoundError, ValueError, TypeError, AttributeError)):
            return False
        status_code = GeminiFlashLiteWordTranslationService._exception_status_code(exc)
        if isinstance(status_code, int):
            return status_code in {408, 429, 500, 502, 503, 504}
        message = str(exc).lower()
        return any(
            token in message
            for token in (
                "timeout",
                "timed out",
                "connection reset",
                "connection aborted",
                "temporarily unavailable",
                "service unavailable",
                "rate limit",
                "429",
            )
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
        if not raw:
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            parsed = json.loads(cleaned)
        except ValueError:
            return _normalize_translation_value(cleaned)
        if isinstance(parsed, dict):
            value = parsed.get("translation")
            if isinstance(value, str):
                return _normalize_translation_value(value)
        if isinstance(parsed, str):
            return _normalize_translation_value(parsed)
        return None

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
        if isinstance(payload, BatchContextualWordTranslationResponse):
            return payload
        if isinstance(payload, dict):
            items = payload.get("items")
        else:
            items = None
        if not isinstance(items, list):
            return None

        expected = set(expected_ids)
        parsed_items: list[BatchContextualWordTranslationResponseItem] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or item_id not in expected:
                continue
            translation = item.get("translation")
            parsed_items.append(
                BatchContextualWordTranslationResponseItem(
                    id=item_id,
                    translation=_normalize_translation_value(translation),
                )
            )
        return BatchContextualWordTranslationResponse(items=parsed_items)

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

    def _parse_meaning_section_payload(self, payload: object, *, valid_ids: set[int]) -> int | None:
        if not isinstance(payload, dict):
            return None
        value = payload.get("meaning_section_id")
        if not isinstance(value, int):
            return None
        if value not in valid_ids:
            return None
        return value


def _normalize_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned.lower()

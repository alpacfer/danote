from __future__ import annotations

from dataclasses import dataclass, field
import json
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


class GeminiWordTranslationService(Protocol):
    provider: str

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None: ...


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
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def close(self) -> None:
        self._client = None

    def translate_word(self, payload: ContextualWordTranslationInput) -> str | None:
        prompt = self._translation_prompt(payload)
        raw = self._generate_text(prompt)
        return self._parse_translation(raw)

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
                "You translate Danish words into the exact English word or short phrase that matches the supplied "
                "dictionary context.\n"
                "Use the morphology, gloss, and lemma to choose the exact inflected English output.\n"
            )
        else:
            task_instruction = (
                "You translate a single Danish word into the exact English word or short phrase.\n"
                "Use the lemma and surface form to choose the right English translation.\n"
            )
        return (
            task_instruction
            + "Return JSON only: {\"translation\":\"...\"}\n"
            + "Rules:\n"
            + "- Output only the English translation.\n"
            + "- Preserve inflection when morphology requires it.\n"
            + "- Keep articles or function words only when needed for the exact form.\n"
            + "- Do not explain your reasoning.\n"
            + f"Context:\n{json.dumps(context, ensure_ascii=False)}"
        )

    def _generate_text(self, prompt: str) -> str | None:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                response = client.models.generate_content(model=self.model, contents=prompt)
                text = getattr(response, "text", None)
                cleaned = text.strip() if isinstance(text, str) else ""
                return cleaned or None
            except Exception as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_seconds * (2**attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise GeminiTranslationError(f"Gemini word translation request failed: {exc}") from exc
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


def _normalize_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned.lower()

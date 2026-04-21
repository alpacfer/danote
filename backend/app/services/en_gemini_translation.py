from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field


_UD_POS_LABELS = {
    "NOUN": "noun",
    "VERB": "verb",
    "ADJ": "adjective",
    "ADV": "adverb",
    "PROPN": "proper noun",
    "INTJ": "interjection",
    "CCONJ": "conjunction",
    "ADP": "preposition",
    "PRON": "pronoun",
    "NUM": "numeral",
    "DET": "determiner",
    "PART": "particle",
    "X": "word",
}


class ENGeminiTranslationError(RuntimeError):
    pass


@dataclass
class ENGeminiTranslationService:
    """Thin Gemini client for English-lemma → Danish-lemma with POS+gloss context."""

    api_key: str
    model: str = "gemini-3.1-flash-lite-preview"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    provider: str = field(default="en_gemini_translation", init=False)
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        key = self.api_key.strip()
        model = self.model.strip()
        if not key:
            raise ENGeminiTranslationError("Gemini API key is required.")
        if not model:
            raise ENGeminiTranslationError("Gemini model is required.")
        self.api_key = key
        self.model = model

    def close(self) -> None:
        self._client = None

    def translate_english_lemma(
        self,
        *,
        lemma: str,
        pos_ud: str | None,
        gloss: str | None,
    ) -> str | None:
        prompt = self._build_prompt(lemma=lemma, pos_ud=pos_ud, gloss=gloss)
        response = self._generate_content(prompt)
        return self._parse(response)

    def _build_prompt(self, *, lemma: str, pos_ud: str | None, gloss: str | None) -> str:
        pos_label = _UD_POS_LABELS.get((pos_ud or "").upper(), "word")
        gloss_clean = (gloss or "").strip()
        gloss_line = f'Meaning: "{gloss_clean}".' if gloss_clean else ""
        return (
            f"Translate the English {pos_label} \"{lemma}\" into Danish.\n"
            f"{gloss_line}\n"
            "Respond with a single Danish lemma appropriate for this meaning and part of speech, "
            "using the base (dictionary/infinitive) form. "
            'Reply strictly as JSON: {"translation": "<danish-word>"}. '
            "If no good translation exists, use null."
        )

    def _generate_content(self, prompt: str) -> object:
        attempts = self.max_retries + 1
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                genai_types = self._genai_types()
                return client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema={
                            "type": "OBJECT",
                            "properties": {
                                "translation": {"type": "STRING", "nullable": True},
                            },
                            "required": ["translation"],
                        },
                        temperature=0,
                        max_output_tokens=64,
                        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
                    ),
                )
            except Exception as exc:
                last_exc = exc
                if attempt < self.max_retries:
                    delay = self.backoff_seconds * (2**attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise ENGeminiTranslationError(
                    f"Gemini EN→DA translation failed: {exc}"
                ) from exc
        raise ENGeminiTranslationError(
            f"Gemini EN→DA translation failed after retries: {last_exc}"
        )

    def _parse(self, response: object) -> str | None:
        parsed = getattr(response, "parsed", None)
        value = _extract_translation(parsed)
        if value is not None:
            return value

        raw = getattr(response, "text", None)
        if not isinstance(raw, str):
            return None
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return None
        return _extract_translation(payload)

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise ENGeminiTranslationError(
                    "google-genai package is required for Gemini EN→DA translation."
                ) from exc
            genai_types = self._genai_types()
            timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    def _genai_types(self):
        try:
            from google.genai import types as genai_types  # type: ignore import-not-found
        except ImportError as exc:
            raise ENGeminiTranslationError(
                "google-genai package is required for Gemini EN→DA translation."
            ) from exc
        return genai_types


def _extract_translation(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("translation")
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None

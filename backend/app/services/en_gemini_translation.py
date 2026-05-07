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
    model: str = "gemini-3.1-flash-lite"
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

    def describe_translation_choices(self, *, query: str, choices: list[dict[str, object]]) -> dict[str, str]:
        if not choices:
            return {}
        prompt = self._build_disambiguation_prompt(query=query, choices=choices)
        response = self._generate_content(
            prompt,
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "id": {"type": "STRING"},
                                "description": {"type": "STRING", "nullable": True},
                            },
                            "required": ["id", "description"],
                        },
                    },
                },
                "required": ["items"],
            },
            max_output_tokens=max(128, min(1024, len(choices) * 48)),
        )
        return self._parse_descriptions(response, valid_ids={str(choice.get("id")) for choice in choices})

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

    def _build_disambiguation_prompt(self, *, query: str, choices: list[dict[str, object]]) -> str:
        return (
            "Write short English UI labels that disambiguate Danish translations of one English search word.\n"
            "Return JSON only with this exact shape: "
            "{\"items\":[{\"id\":\"0\",\"description\":\"...\"}]}\n"
            "Rules:\n"
            "- Return exactly one item for every input id and copy ids exactly.\n"
            "- description must be 2 to 5 plain English words.\n"
            "- Describe the meaning, not grammar, not the Danish word, and not the English query itself.\n"
            "- Use the supplied glosses/examples only as sense clues.\n"
            "- No full sentences, punctuation, quotes, or explanations.\n"
            "- Prefer learner-friendly labels such as 'wax light', 'inspect eggs', or 'bad quality stuff'.\n"
            f"English query: {query}\n"
            f"Choices:\n{json.dumps(choices, ensure_ascii=False)}"
        )

    def _generate_content(
        self,
        prompt: str,
        *,
        response_schema: dict[str, object] | None = None,
        max_output_tokens: int = 64,
    ) -> object:
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
                        response_schema=response_schema or {
                            "type": "OBJECT",
                            "properties": {
                                "translation": {"type": "STRING", "nullable": True},
                            },
                            "required": ["translation"],
                        },
                        temperature=0,
                        max_output_tokens=max_output_tokens,
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

    def _parse_descriptions(self, response: object, *, valid_ids: set[str]) -> dict[str, str]:
        parsed = getattr(response, "parsed", None)
        extracted = _extract_descriptions(parsed, valid_ids=valid_ids)
        if extracted:
            return extracted

        raw = getattr(response, "text", None)
        if not isinstance(raw, str):
            return {}
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload = json.loads(cleaned)
        except ValueError:
            return {}
        return _extract_descriptions(payload, valid_ids=valid_ids)

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


def _extract_descriptions(payload: object, *, valid_ids: set[str]) -> dict[str, str]:
    if not isinstance(payload, dict):
        return {}
    items = payload.get("items")
    if not isinstance(items, list):
        return {}
    descriptions: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in valid_ids:
            continue
        description = item.get("description")
        if not isinstance(description, str):
            continue
        cleaned = " ".join(description.strip().split()).strip(".,;:!?\"'")
        if cleaned:
            descriptions[item_id] = cleaned
    return descriptions

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Literal, Protocol


class RelatedWordsError(RuntimeError):
    """Raised when Gemini related-word analysis cannot be completed."""


RelatedWordPosTag = Literal["ADJ", "ADV", "NOUN", "VERB"]


@dataclass(frozen=True, slots=True)
class RelatedWordItem:
    lemma: str
    english_translation: str
    pos_tag: RelatedWordPosTag


@dataclass(frozen=True, slots=True)
class RelatedWordsResult:
    items: list[RelatedWordItem]


class GeminiRelatedWordsService(Protocol):
    provider: str

    def find_related_words(self, *, lemma: str) -> RelatedWordsResult: ...


@dataclass
class GeminiCompoundRelatedWordsService:
    api_key: str
    model: str = "gemini-3.1-flash-lite-preview"
    timeout_seconds: float = 20.0
    provider: str = field(default="gemini_related_words", init=False)
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        if not normalized_key:
            raise RelatedWordsError("Gemini API key is required for related-word analysis.")
        if not normalized_model:
            raise RelatedWordsError("Gemini model is required for related-word analysis.")
        self.api_key = normalized_key
        self.model = normalized_model

    def close(self) -> None:
        self._client = None

    def find_related_words(self, *, lemma: str) -> RelatedWordsResult:
        normalized_lemma = " ".join(lemma.strip().split()).lower()
        if not normalized_lemma:
            return RelatedWordsResult(items=[])
        response = self._generate_content(
            self._prompt(normalized_lemma),
            config=self._response_config(),
        )
        text = getattr(response, "text", None)
        return self._parse_response(text, lemma=normalized_lemma)

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise RelatedWordsError("google-genai package is required for related-word analysis.") from exc
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
            raise RelatedWordsError("google-genai package is required for related-word analysis.") from exc
        return genai_types

    def _generate_content(self, prompt: str, *, config: object) -> object:
        client = self._ensure_client()
        try:
            return client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as exc:
            raise RelatedWordsError(f"Gemini related-word request failed: {exc}") from exc

    def _response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "is_compound": {"type": "BOOLEAN"},
                    "items": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "lemma": {"type": "STRING"},
                                "english_translation": {"type": "STRING"},
                                "pos_tag": {
                                    "type": "STRING",
                                    "enum": ["ADJ", "ADV", "NOUN", "VERB"],
                                },
                            },
                            "required": ["lemma", "english_translation", "pos_tag"],
                        },
                    },
                },
                "required": ["is_compound", "items"],
            },
            temperature=0,
            max_output_tokens=256,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _prompt(self, lemma: str) -> str:
        return (
            "You are a Danish linguist.\n"
            "Analyze one Danish lemma.\n"
            "This task is ONLY for compound decomposition.\n"
            "Return JSON only.\n"
            "{"
            '"is_compound":true,'
            '"items":[{"lemma":"...","english_translation":"...","pos_tag":"NOUN|VERB|ADJ|ADV"}]'
            "}\n"
            "Rules:\n"
            "- If the lemma is not a compound, set is_compound=false and items=[].\n"
            "- Return only direct compound components, in reading order.\n"
            "- Each item lemma must be the canonical Danish lemma, lowercased.\n"
            "- english_translation must be a short idiomatic English gloss.\n"
            "- pos_tag must be one of NOUN, VERB, ADJ, ADV.\n"
            "- Do not include explanations or uncertainty text.\n"
            f"Lemma:\n{json.dumps({'lemma': lemma}, ensure_ascii=False)}"
        )

    def _parse_response(self, raw: object, *, lemma: str) -> RelatedWordsResult:
        text = raw.strip() if isinstance(raw, str) else ""
        if not text:
            return RelatedWordsResult(items=[])
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise RelatedWordsError("Gemini related-word response was not valid JSON.") from exc
        if not isinstance(payload, dict):
            raise RelatedWordsError("Gemini related-word response must be a JSON object.")
        if not bool(payload.get("is_compound")):
            return RelatedWordsResult(items=[])
        raw_items = payload.get("items")
        if not isinstance(raw_items, list):
            raise RelatedWordsError("Gemini related-word response items must be a list.")

        items: list[RelatedWordItem] = []
        seen: set[tuple[str, str]] = set()
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            item_lemma = " ".join(str(raw_item.get("lemma", "")).strip().split()).lower()
            english_translation = " ".join(str(raw_item.get("english_translation", "")).strip().split())
            pos_tag = str(raw_item.get("pos_tag", "")).strip().upper()
            if (
                not item_lemma
                or item_lemma == lemma
                or not english_translation
                or pos_tag not in {"ADJ", "ADV", "NOUN", "VERB"}
            ):
                continue
            key = (item_lemma, pos_tag)
            if key in seen:
                continue
            seen.add(key)
            items.append(
                RelatedWordItem(
                    lemma=item_lemma,
                    english_translation=english_translation,
                    pos_tag=pos_tag,
                )
            )
        return RelatedWordsResult(items=items)

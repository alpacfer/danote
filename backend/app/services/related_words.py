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


@dataclass(frozen=True, slots=True)
class GlossVariantCandidate:
    cor_id: str
    gloss: str | None
    gloss_translation: str | None
    gram_raw: str


class GeminiRelatedWordsService(Protocol):
    provider: str

    def find_related_words(self, *, lemma: str) -> RelatedWordsResult: ...

    def pick_gloss_variant(
        self,
        *,
        lemma: str,
        english_translation: str | None,
        pos_tag: str | None,
        candidates: list[GlossVariantCandidate],
    ) -> str | None:
        """Return the cor_id of the best-matching candidate, or None if uncertain."""
        ...


@dataclass
class GeminiCompoundRelatedWordsService:
    api_key: str
    model: str = "gemini-3.1-flash-lite"
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

    def pick_gloss_variant(
        self,
        *,
        lemma: str,
        english_translation: str | None,
        pos_tag: str | None,
        candidates: list[GlossVariantCandidate],
    ) -> str | None:
        if len(candidates) < 2:
            return candidates[0].cor_id if candidates else None
        try:
            response = self._generate_content(
                self._pick_gloss_prompt(lemma, english_translation, pos_tag, candidates),
                config=self._pick_gloss_response_config(),
            )
            text = getattr(response, "text", None)
            return self._parse_pick_gloss_response(text, candidates=candidates)
        except RelatedWordsError:
            return None

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
        is_mwe = " " in lemma.strip()
        if is_mwe:
            # Multi-word expression (phrasal verb / idiom): the lemma has whitespace
            # (e.g. "passe på", "tage af sted", "skyde papegøjen"). Return the
            # constituent words AND any close-meaning near-synonym MWEs in reading
            # order. The schema is unchanged so the worker can persist either shape.
            return (
                "You are a Danish linguist.\n"
                "Analyze one Danish multi-word expression (phrasal verb or idiom).\n"
                "Return JSON only.\n"
                "{"
                '"is_compound":true,'
                '"items":[{"lemma":"...","english_translation":"...","pos_tag":"NOUN|VERB|ADJ|ADV|ADP|CCONJ|SCONJ|PART"}]'
                "}\n"
                "Rules:\n"
                "- Always set is_compound=true; the lemma is a multi-word expression.\n"
                "- items must include EVERY constituent word in reading order first (e.g. for \"passe på\" return [\"passe\", \"på\"]).\n"
                "- After the constituents, you MAY append up to 3 close-meaning near-synonym MWEs (e.g. \"holde øje med\" for \"passe på\") in order of semantic closeness.\n"
                "- Each item lemma must be the canonical Danish lemma, lowercased.\n"
                "- english_translation must be a short idiomatic English gloss.\n"
                "- pos_tag must be the standard UD tag for that constituent (ADP for prepositions like \"på\", VERB for the head verb, etc.).\n"
                "- Do not include explanations or uncertainty text.\n"
                f"Lemma:\n{json.dumps({'lemma': lemma}, ensure_ascii=False)}"
            )
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

    def _pick_gloss_prompt(
        self,
        lemma: str,
        english_translation: str | None,
        pos_tag: str | None,
        candidates: list[GlossVariantCandidate],
    ) -> str:
        lines = [
            "You are a Danish linguist selecting the correct dictionary sense.",
            f"Danish lemma: {json.dumps(lemma, ensure_ascii=False)}",
        ]
        if english_translation:
            lines.append(f"Known English meaning: {json.dumps(english_translation, ensure_ascii=False)}")
        if pos_tag:
            lines.append(f"Part of speech: {pos_tag}")
        lines.append("Dictionary entries (0-indexed):")
        for i, c in enumerate(candidates):
            gloss_display = c.gloss_translation or c.gloss or "(no gloss)"
            lines.append(f"  {i}: gloss={json.dumps(gloss_display, ensure_ascii=False)}, gram={json.dumps(c.gram_raw, ensure_ascii=False)}")
        lines.append(
            'Return JSON: {"selected_index": <integer index of best match, or null if uncertain>}\n'
            "Rules:\n"
            "- Select null only when truly ambiguous — prefer a definite answer.\n"
            "- Do not add explanations."
        )
        return "\n".join(lines)

    def _pick_gloss_response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "selected_index": {"type": "INTEGER", "nullable": True},
                },
                "required": ["selected_index"],
            },
            temperature=0,
            max_output_tokens=64,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _parse_pick_gloss_response(
        self, raw: object, *, candidates: list[GlossVariantCandidate]
    ) -> str | None:
        text = raw.strip() if isinstance(raw, str) else ""
        if not text:
            return None
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if not isinstance(payload, dict):
            return None
        idx = payload.get("selected_index")
        if idx is None:
            return None
        try:
            idx = int(idx)
        except (TypeError, ValueError):
            return None
        if idx < 0 or idx >= len(candidates):
            return None
        return candidates[idx].cor_id

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

        # For MWE lemmas (multi-word: "passe på", "tage af sted") the constituents
        # may be prepositions, conjunctions, or particles — broaden the allowed
        # POS set in that case. Single-word compound decomposition stays strict.
        is_mwe_lemma = " " in lemma.strip()
        allowed_pos = (
            {"ADJ", "ADV", "NOUN", "VERB", "ADP", "CCONJ", "SCONJ", "PART"}
            if is_mwe_lemma
            else {"ADJ", "ADV", "NOUN", "VERB"}
        )

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
                or pos_tag not in allowed_pos
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

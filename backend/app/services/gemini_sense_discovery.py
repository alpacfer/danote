from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any

from app.services.gemini_result_cache import GeminiResultCache
from app.services.gemini_translation_helpers import normalize_translation_value


@dataclass(frozen=True, slots=True)
class SenseDiscoveryCorCandidate:
    cor_id: str
    lemma: str
    gloss: str | None = None
    pos_tag: str | None = None
    lemma_idx: int | None = None


@dataclass(frozen=True, slots=True)
class SenseDiscoveryInput:
    lemma: str
    pos_tag: str | None = None
    cor_gloss: str | None = None
    cor_candidates: list[SenseDiscoveryCorCandidate] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class DiscoveredSense:
    meaning_key: str
    english_translation: str
    gloss: str
    alternative_translations: list[str] = field(default_factory=list)
    example_da: str | None = None
    example_en: str | None = None
    cor_lemma_idx: int | None = None


@dataclass(frozen=True, slots=True)
class DiscoveredSenseSet:
    senses: list[DiscoveredSense] = field(default_factory=list)


_OPEN_CLASS_POS = {"VERB", "AUX", "NOUN", "PROPN", "ADJ", "ADV"}
_MEANING_KEY_RE = re.compile(r"[^a-z0-9]+")
_MAX_SENSES = 8
_MAX_ALTERNATIVES = 3


def is_sense_discoverable_pos(pos_tag: str | None) -> bool:
    return (pos_tag or "").strip().upper() in _OPEN_CLASS_POS


def cache_key(payload: SenseDiscoveryInput) -> str:
    candidate_idxs = sorted({c.lemma_idx for c in payload.cor_candidates if c.lemma_idx is not None})
    parts = [
        payload.lemma.strip().lower(),
        (payload.pos_tag or "").strip().upper(),
        (payload.cor_gloss or "").strip().lower(),
        ",".join(str(idx) for idx in candidate_idxs),
    ]
    return "sense_discovery::" + "|".join(parts)


def build_sense_discovery_prompt(payload: SenseDiscoveryInput) -> str:
    pos_tag = (payload.pos_tag or "").strip().upper() or None
    lemma_frame = _lemma_frame(payload.lemma, pos_tag)
    cor_candidates = [
        {
            "cor_id": candidate.cor_id,
            "lemma": candidate.lemma,
            "lemma_idx": candidate.lemma_idx,
            "pos_tag": candidate.pos_tag,
            "gloss_da": candidate.gloss,
        }
        for candidate in payload.cor_candidates
    ]
    context = {
        "lemma_da": payload.lemma,
        "lemma_frame_da": lemma_frame,
        "pos_tag": pos_tag,
        "cor_gloss_da": payload.cor_gloss,
        "cor_candidates": cor_candidates,
    }
    verb_rule = (
        "- For verbs, english_translation must be an English infinitive phrase ('to hit', 'to mow').\n"
        if pos_tag in {"VERB", "AUX"}
        else ""
    )
    cor_rule = (
        "- When a sense corresponds to one of cor_candidates, set cor_lemma_idx to that candidate's lemma_idx.\n"
        if cor_candidates
        else "- Leave cor_lemma_idx null; no COR candidates were supplied.\n"
    )
    return (
        "You enumerate the distinct dictionary senses of one Danish lemma for a language-learning wordbank.\n"
        "Return JSON only with this exact shape: "
        "{\"senses\":[{\"meaning_key\":\"...\",\"english_translation\":\"...\","
        "\"gloss\":\"...\",\"alternative_translations\":[\"...\"],"
        "\"example_da\":\"...\",\"example_en\":\"...\",\"cor_lemma_idx\":null}]}\n"
        "Rules:\n"
        "- Each sense must be semantically distinct from every other sense in the list.\n"
        "- Synonyms of the same sense (e.g. 'to beat', 'to strike' for 'hit') belong in alternative_translations, not as separate senses.\n"
        "- meaning_key must be a short, stable, lowercase ASCII slug (a-z, 0-9, hyphens) for this sense — e.g. 'hit', 'mow', 'ring-bell'.\n"
        "- meaning_keys must be unique across the senses list.\n"
        "- english_translation must be the single best modern dictionary-style English translation for this sense.\n"
        "- gloss must be a short Danish definition for this sense (one short phrase, no quotes).\n"
        "- alternative_translations are obvious popular English synonyms for the same sense. Cap at 3. May be empty.\n"
        "- example_da is one short natural Danish sentence that demonstrates this sense; example_en is its English translation. Both may be null if no good example fits.\n"
        f"- Order senses by frequency (most common first). Cap at {_MAX_SENSES} senses.\n"
        "- Do not invent senses; if the lemma is monosemous return exactly one sense.\n"
        + verb_rule
        + cor_rule
        + "- Do not explain your reasoning.\n"
        f"Context:\n{json.dumps(context, ensure_ascii=False)}"
    )


def sense_discovery_response_config(genai_types) -> object:
    return genai_types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema={
            "type": "OBJECT",
            "properties": {
                "senses": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "meaning_key": {"type": "STRING"},
                            "english_translation": {"type": "STRING"},
                            "gloss": {"type": "STRING"},
                            "alternative_translations": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                            },
                            "example_da": {"type": "STRING", "nullable": True},
                            "example_en": {"type": "STRING", "nullable": True},
                            "cor_lemma_idx": {"type": "INTEGER", "nullable": True},
                        },
                        "required": [
                            "meaning_key",
                            "english_translation",
                            "gloss",
                            "alternative_translations",
                        ],
                    },
                }
            },
            "required": ["senses"],
        },
        temperature=0,
        max_output_tokens=1536,
        thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
    )


def parse_sense_discovery_payload(payload: object) -> DiscoveredSenseSet | None:
    raw_senses: Any
    if isinstance(payload, DiscoveredSenseSet):
        return payload
    if isinstance(payload, dict):
        raw_senses = payload.get("senses")
    else:
        return None
    if not isinstance(raw_senses, list):
        return None

    senses: list[DiscoveredSense] = []
    seen_keys: set[str] = set()
    for raw_sense in raw_senses:
        if not isinstance(raw_sense, dict):
            continue
        sense = _parse_single_sense(raw_sense, seen_keys)
        if sense is None:
            continue
        senses.append(sense)
        if len(senses) >= _MAX_SENSES:
            break
    return DiscoveredSenseSet(senses=senses)


def discover_senses_with_gemini(
    payload: SenseDiscoveryInput,
    *,
    cache: GeminiResultCache | None,
    generate_content: Callable[[str, object], object],
    genai_types_factory: Callable[[], object],
) -> DiscoveredSenseSet | None:
    """Run sense discovery against Gemini with caching + lenient JSON parsing.

    Extracted from the Gemini service so the prompt/parser/cache stay in one
    module instead of fattening the multi-method service file past its budget.
    """
    key = cache_key(payload)
    cached = _cache_get(cache, key)
    cached_set = deserialize_sense_set(cached)
    if cached_set is not None:
        return cached_set
    response = generate_content(
        build_sense_discovery_prompt(payload),
        sense_discovery_response_config(genai_types_factory()),
    )
    parsed_payload = getattr(response, "parsed", None)
    parsed = parse_sense_discovery_payload(parsed_payload)
    if parsed is None:
        raw_text = getattr(response, "text", None)
        if not isinstance(raw_text, str):
            return None
        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()
        try:
            payload_dict = json.loads(cleaned)
        except ValueError:
            return None
        parsed = parse_sense_discovery_payload(payload_dict)
    if parsed is not None and parsed.senses:
        _cache_put(cache, key, serialize_sense_set(parsed))
    return parsed


def _cache_get(cache: GeminiResultCache | None, key: str) -> str | None:
    if cache is None:
        return None
    try:
        return cache.get(key)
    except (OSError, sqlite3.DatabaseError):
        return None


def _cache_put(cache: GeminiResultCache | None, key: str, value: str) -> None:
    if cache is None:
        return
    try:
        cache.put(key, value)
    except (OSError, sqlite3.DatabaseError):
        return


def serialize_sense_set(sense_set: DiscoveredSenseSet) -> str:
    return json.dumps({"senses": [asdict(sense) for sense in sense_set.senses]}, ensure_ascii=False)


def deserialize_sense_set(raw: str | None) -> DiscoveredSenseSet | None:
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None
    return parse_sense_discovery_payload(payload)


def _parse_single_sense(raw_sense: dict[str, Any], seen_keys: set[str]) -> DiscoveredSense | None:
    english_translation = normalize_translation_value(raw_sense.get("english_translation"))
    gloss = normalize_translation_value(raw_sense.get("gloss"))
    if not english_translation or not gloss:
        return None

    meaning_key_raw = raw_sense.get("meaning_key")
    meaning_key = _normalize_meaning_key(meaning_key_raw) or _normalize_meaning_key(english_translation)
    if not meaning_key or meaning_key in seen_keys:
        return None
    seen_keys.add(meaning_key)

    alternatives = _normalize_alternatives(
        raw_sense.get("alternative_translations"),
        primary=english_translation,
    )
    example_da = _normalize_example_text(raw_sense.get("example_da"))
    example_en = _normalize_example_text(raw_sense.get("example_en"))
    cor_lemma_idx = _normalize_int(raw_sense.get("cor_lemma_idx"))
    return DiscoveredSense(
        meaning_key=meaning_key,
        english_translation=english_translation,
        gloss=gloss,
        alternative_translations=alternatives,
        example_da=example_da,
        example_en=example_en,
        cor_lemma_idx=cor_lemma_idx,
    )


def _normalize_meaning_key(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    lowered = value.strip().lower()
    if not lowered:
        return None
    slug = _MEANING_KEY_RE.sub("-", lowered).strip("-")
    return slug or None


def _normalize_alternatives(value: Any, *, primary: str) -> list[str]:
    if not isinstance(value, list):
        return []
    seen: set[str] = set()
    alternatives: list[str] = []
    for raw in value:
        normalized = normalize_translation_value(raw)
        if normalized is None or normalized == primary or normalized in seen:
            continue
        seen.add(normalized)
        alternatives.append(normalized)
        if len(alternatives) >= _MAX_ALTERNATIVES:
            break
    return alternatives


def _normalize_example_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    return cleaned or None


def _normalize_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _lemma_frame(lemma: str | None, pos_tag: str | None) -> str | None:
    normalized_lemma = " ".join((lemma or "").strip().split())
    if not normalized_lemma:
        return None
    if (pos_tag or "").upper() in {"VERB", "AUX"}:
        return f"at {normalized_lemma}"
    return normalized_lemma


__all__ = [
    "DiscoveredSense",
    "DiscoveredSenseSet",
    "SenseDiscoveryCorCandidate",
    "SenseDiscoveryInput",
    "build_sense_discovery_prompt",
    "cache_key",
    "deserialize_sense_set",
    "discover_senses_with_gemini",
    "is_sense_discoverable_pos",
    "parse_sense_discovery_payload",
    "sense_discovery_response_config",
    "serialize_sense_set",
]

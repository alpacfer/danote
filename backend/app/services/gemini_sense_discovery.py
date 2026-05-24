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
    english_gloss: str | None = None
    alternative_translations: list[str] = field(default_factory=list)
    example_da: str | None = None
    example_en: str | None = None
    cor_lemma_idx: int | None = None


@dataclass(frozen=True, slots=True)
class DiscoveredSenseSet:
    senses: list[DiscoveredSense] = field(default_factory=list)


_OPEN_CLASS_POS = {"VERB", "AUX", "NOUN", "PROPN", "ADJ", "ADV"}
_MEANING_KEY_RE = re.compile(r"[^a-z0-9]+")
_MAX_SENSES = 6
_MAX_ALTERNATIVES = 4
# Bump this token whenever the prompt or merge policy changes so cached
# Gemini results from older policies are naturally invalidated.
_PROMPT_VERSION = "v4-bilingual-gloss"


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
    return f"sense_discovery::{_PROMPT_VERSION}::" + "|".join(parts)


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
        "You enumerate the DISTINCT dictionary senses of one Danish lemma for a learner's wordbank.\n"
        "The learner wants ONE card per genuinely different meaning. Aggressively merge anything that\n"
        "a Danish speaker would consider 'the same idea, just a different English word' into a single\n"
        "card whose alternative_translations carries the other phrasings.\n"
        "Return JSON only with this exact shape: "
        "{\"senses\":[{\"meaning_key\":\"...\",\"english_translation\":\"...\","
        "\"gloss\":\"...\",\"english_gloss\":\"...\","
        "\"alternative_translations\":[\"...\"],"
        "\"example_da\":\"...\",\"example_en\":\"...\",\"cor_lemma_idx\":null}]}\n"
        "MERGE TEST (apply per pair of candidate senses):\n"
        "  If a fluent Danish-English bilingual would routinely use both English words to translate the\n"
        "  same Danish sentence with this lemma without any change in meaning, they are the SAME sense\n"
        "  — emit one card whose english_translation is the more common one and put the other in\n"
        "  alternative_translations.\n"
        "  Only split into two cards when the senses cannot share an example sentence — i.e. swapping\n"
        "  the English word in the example would mistranslate the Danish.\n"
        "MERGE EXAMPLES (do this):\n"
        "  - holde: 'to hold' and 'to keep' → ONE card { english_translation: 'to hold',\n"
        "    alternative_translations: ['to keep'] }. Both translate 'jeg holder bogen' / 'jeg holder det\n"
        "    hemmeligt' interchangeably.\n"
        "  - gå: 'to walk' and 'to go (on foot)' → ONE card { english_translation: 'to walk',\n"
        "    alternative_translations: ['to go'] }.\n"
        "  - slå: 'to hit', 'to strike', 'to beat' → ONE card { english_translation: 'to hit',\n"
        "    alternative_translations: ['to strike', 'to beat'] }.\n"
        "SPLIT EXAMPLES (do NOT merge these):\n"
        "  - holde: 'to hold/keep' vs 'to stop' vs 'to host (an event)' → three cards. 'Bussen holder'\n"
        "    cannot be translated with 'hold' or 'host'.\n"
        "  - slå: 'to hit' vs 'to mow (a lawn)' vs 'to ring (bells)' vs 'to fold (paper)' → distinct\n"
        "    cards; you cannot mow with 'hit' or ring a bell with 'fold'.\n"
        "  - gå: 'to walk' vs 'to leave' vs 'to work/function (a machine)' → distinct cards.\n"
        "Other rules:\n"
        "- meaning_key: short, stable, lowercase ASCII slug (a-z, 0-9, hyphens) for the merged sense\n"
        "  — e.g. 'hold', 'stop', 'host-event', 'mow', 'ring-bell'. Unique across the list.\n"
        "- english_translation: the single most common modern dictionary-style English translation.\n"
        "- NO TRANSLATION REUSE ACROSS SENSES. Every English phrasing (english_translation or any\n"
        "  alternative_translations entry) must appear on AT MOST ONE card across the whole response.\n"
        "  If the same word fits two senses, decide which is its primary sense and put it there only.\n"
        "  Example: 'to hold' belongs to the 'hold/keep' sense; it must NOT also appear under 'host-event'\n"
        "  (which should use 'to host', 'to throw', 'to organize' instead).\n"
        "- gloss: a short Danish definition for the merged sense (one short phrase, no quotes).\n"
        "- english_gloss: a short English equivalent of that same definition — the\n"
        "  English text a Danish-English dictionary would print after the headword.\n"
        "  Must be English (never Danish). Do NOT just repeat english_translation; the\n"
        "  english_gloss is a descriptive phrase (e.g. 'a piece of stiff paper used in\n"
        "  games' for the 'playing card' sense of 'kort'). One short phrase, no quotes,\n"
        "  no parentheses. Must be present for every sense.\n"
        f"- alternative_translations: ≤{_MAX_ALTERNATIVES} other common English phrasings for the SAME merged\n"
        "  sense. May be empty when no equally common alternative exists. Do not repeat english_translation.\n"
        "- example_da / example_en: one short Danish sentence that demonstrates this merged sense,\n"
        "  plus its English translation. Both may be null if no good example fits.\n"
        f"- Order senses by everyday frequency (most common first). Hard cap: {_MAX_SENSES} senses.\n"
        "- Prefer fewer cards. If two candidate senses fail the MERGE TEST only at the edges (rare\n"
        "  idioms, archaic uses), still merge them and keep the rare phrasing out of\n"
        "  alternative_translations.\n"
        "- If the lemma is monosemous, return exactly one sense.\n"
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
                            "english_gloss": {"type": "STRING"},
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
                            "english_gloss",
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
    senses = _deduplicate_translations_across_senses(senses)
    return DiscoveredSenseSet(senses=senses)


def _deduplicate_translations_across_senses(
    senses: list[DiscoveredSense],
) -> list[DiscoveredSense]:
    """Strip any English phrasing that appears on more than one sense card.

    Gemini occasionally reuses the same translation as a primary on one card
    and as an alternative on another (e.g. 'to hold' showing up under both
    'hold/keep' and 'host-event' for ``holde``). That makes adjacent search
    cards look like the same meaning. We keep the phrasing on the card where
    it first appears as the english_translation (or first appears at all)
    and drop it everywhere else.
    """
    if len(senses) <= 1:
        return senses
    claimed: set[str] = set()
    # First pass: claim every primary translation. Primaries always win over
    # alternatives because they're the dominant phrasing for that card.
    for sense in senses:
        claimed.add(sense.english_translation.lower())
    deduped: list[DiscoveredSense] = []
    seen_alternatives: set[str] = set()
    for sense in senses:
        filtered_alternatives: list[str] = []
        for alternative in sense.alternative_translations:
            alt_key = alternative.lower()
            if alt_key in claimed and alt_key != sense.english_translation.lower():
                # This phrasing is some other card's primary — drop it here.
                continue
            if alt_key in seen_alternatives:
                # Already used as an alternative on an earlier card.
                continue
            seen_alternatives.add(alt_key)
            filtered_alternatives.append(alternative)
        if filtered_alternatives == list(sense.alternative_translations):
            deduped.append(sense)
        else:
            deduped.append(
                DiscoveredSense(
                    meaning_key=sense.meaning_key,
                    english_translation=sense.english_translation,
                    gloss=sense.gloss,
                    english_gloss=sense.english_gloss,
                    alternative_translations=filtered_alternatives,
                    example_da=sense.example_da,
                    example_en=sense.example_en,
                    cor_lemma_idx=sense.cor_lemma_idx,
                )
            )
    return deduped


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
    english_gloss = normalize_translation_value(raw_sense.get("english_gloss"))
    # Reject the case where Gemini echoed the lemma translation back into
    # english_gloss — that adds no info and the UI would render it as a
    # redundant parenthetical ("playing card (playing card)").
    if english_gloss is not None and english_gloss == english_translation:
        english_gloss = None
    example_da = _normalize_example_text(raw_sense.get("example_da"))
    example_en = _normalize_example_text(raw_sense.get("example_en"))
    cor_lemma_idx = _normalize_int(raw_sense.get("cor_lemma_idx"))
    return DiscoveredSense(
        meaning_key=meaning_key,
        english_translation=english_translation,
        gloss=gloss,
        english_gloss=english_gloss,
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

from __future__ import annotations

import hashlib
import json
from typing import Protocol

CACHE_SCHEMA_VERSION = "en-gemini-v1"


class ENGeminiBatchService(Protocol):
    def _cache_get(self, key: str) -> str | None: ...

    def _cache_put(self, key: str, value: str) -> None: ...

    def _generate_content(
        self,
        prompt: str,
        *,
        response_schema: dict[str, object] | None = None,
        max_output_tokens: int = 64,
    ) -> object: ...


def translate_english_lemmas_batch(
    service: ENGeminiBatchService,
    *,
    query: str,
    candidates: list[dict[str, object]],
) -> dict[str, str | None]:
    if not candidates:
        return {}
    results: dict[str, str | None] = {}
    uncached: list[dict[str, object]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("id") or "")
        if not candidate_id:
            continue
        cache_key = translation_cache_key_for_candidate(candidate)
        cached = service._cache_get(cache_key)
        if cached is None:
            uncached.append(candidate)
            continue
        loaded = json_loads(cached)
        results[candidate_id] = loaded if isinstance(loaded, str) or loaded is None else None
    if not uncached:
        return results

    valid_ids = {str(candidate.get("id")) for candidate in uncached}
    response = service._generate_content(
        _build_batch_translation_prompt(query=query, candidates=uncached),
        response_schema={
            "type": "OBJECT",
            "properties": {
                "items": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "id": {"type": "STRING"},
                            "translation": {"type": "STRING", "nullable": True},
                        },
                        "required": ["id", "translation"],
                    },
                },
            },
            "required": ["items"],
        },
        max_output_tokens=max(128, min(2048, len(uncached) * 48)),
    )
    batch_results = _extract_batch_translations(response_payload(response), valid_ids=valid_ids)
    for candidate in uncached:
        candidate_id = str(candidate.get("id") or "")
        value = batch_results.get(candidate_id)
        results[candidate_id] = value
        service._cache_put(
            translation_cache_key_for_candidate(candidate),
            json.dumps(value, ensure_ascii=False),
        )
    return results


def response_payload(response: object) -> object:
    parsed = getattr(response, "parsed", None)
    if parsed is not None:
        return parsed
    raw = getattr(response, "text", None)
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()
    try:
        return json.loads(cleaned)
    except ValueError:
        return None


def json_loads(value: str) -> object:
    try:
        return json.loads(value)
    except ValueError:
        return None


def normalize_key_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def stable_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def cache_key(namespace: str, *parts: object) -> str:
    payload = stable_json([CACHE_SCHEMA_VERSION, namespace, *parts])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{CACHE_SCHEMA_VERSION}:{namespace}:{digest}"


def translation_cache_key_for_candidate(candidate: dict[str, object]) -> str:
    return cache_key(
        "trans_v1",
        normalize_key_text(str(candidate.get("lemma") or "")),
        str(candidate.get("pos_ud") or "").strip().upper(),
        normalize_key_text(str(candidate.get("gloss") or "")),
    )


def extract_translation(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("translation")
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def extract_match_decisions(payload: object, *, valid_ids: set[str]) -> dict[str, bool]:
    if not isinstance(payload, dict):
        return {}
    items = payload.get("items")
    if not isinstance(items, list):
        return {}
    decisions: dict[str, bool] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in valid_ids:
            continue
        matches = item.get("matches")
        if isinstance(matches, bool):
            decisions[item_id] = matches
    return decisions


def extract_descriptions(payload: object, *, valid_ids: set[str]) -> dict[str, str]:
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


def _build_batch_translation_prompt(*, query: str, candidates: list[dict[str, object]]) -> str:
    return (
        "Translate multiple English lemma candidates into Danish in one batch.\n"
        "Return JSON only with this exact shape: "
        "{\"items\":[{\"id\":\"0\",\"translation\":\"dansk\"}]}\n"
        "Rules:\n"
        "- Return exactly one item for every input id and copy ids exactly.\n"
        "- translation is one Danish base lemma appropriate for that candidate's part of speech and gloss.\n"
        "- Use null if no good translation exists.\n"
        "- Do not reuse the query's most common sense when a candidate gloss/POS points elsewhere.\n"
        f"English query: {query}\n"
        f"Candidates:\n{json.dumps(candidates, ensure_ascii=False)}"
    )


def _extract_batch_translations(payload: object, *, valid_ids: set[str]) -> dict[str, str | None]:
    if not isinstance(payload, dict):
        return {}
    items = payload.get("items")
    if not isinstance(items, list):
        return {}
    translations: dict[str, str | None] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id")
        if not isinstance(item_id, str) or item_id not in valid_ids:
            continue
        value = item.get("translation")
        if value is None:
            translations[item_id] = None
        elif isinstance(value, str):
            cleaned = value.strip()
            translations[item_id] = cleaned or None
    return translations

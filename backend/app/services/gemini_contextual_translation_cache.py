from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from dataclasses import asdict

from app.services.gemini_result_cache import GeminiResultCache
from app.services.gemini_translation_models import ContextualWordTranslationInput

# Bump when the contextual translation prompt or parsing policy changes.
_PROMPT_VERSION = "contextual-word-v1"


def get_cached_contextual_translation(
    cache: GeminiResultCache | None,
    payload: ContextualWordTranslationInput,
) -> str | None:
    if cache is None:
        return None
    try:
        return cache.get(_cache_key(payload))
    except (OSError, sqlite3.DatabaseError):
        return None


def put_cached_contextual_translation(
    cache: GeminiResultCache | None,
    payload: ContextualWordTranslationInput,
    translation: str | None,
) -> None:
    if cache is None or not translation:
        return
    try:
        cache.put(_cache_key(payload), translation)
    except (OSError, sqlite3.DatabaseError):
        return


def resolve_contextual_translation(
    cache: GeminiResultCache | None,
    payload: ContextualWordTranslationInput,
    *,
    generate: Callable[[], str | None],
) -> str | None:
    cached = get_cached_contextual_translation(cache, payload)
    if cached is not None:
        return cached
    translated = generate()
    put_cached_contextual_translation(cache, payload, translated)
    return translated


def partition_cached_contextual_translations(
    cache: GeminiResultCache | None,
    payloads: list[ContextualWordTranslationInput],
) -> tuple[list[str | None], list[tuple[int, ContextualWordTranslationInput]]]:
    results = [get_cached_contextual_translation(cache, payload) for payload in payloads]
    missing = [
        (index, payload)
        for index, (payload, result) in enumerate(zip(payloads, results, strict=False))
        if result is None
    ]
    return results, missing


def merge_contextual_translations(
    cache: GeminiResultCache | None,
    results: list[str | None],
    missing: list[tuple[int, ContextualWordTranslationInput]],
    translations_by_index: dict[str, str | None],
) -> list[str | None]:
    for index, payload in missing:
        translated = translations_by_index.get(str(index))
        results[index] = translated
        put_cached_contextual_translation(cache, payload, translated)
    return results


def _cache_key(payload: ContextualWordTranslationInput) -> str:
    serialized = json.dumps(
        [_PROMPT_VERSION, asdict(payload)],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"gemini-contextual-translation::{_PROMPT_VERSION}::{digest}"

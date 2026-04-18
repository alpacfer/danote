from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import json
from typing import Literal

from app.core.config import BASE_DIR
from app.services.token_classifier import normalize_token

_SELF_TRANSLATION_HELPER_PREFIXES = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "that",
    "the",
    "to",
    "with",
}


@dataclass(frozen=True, slots=True)
class InvalidSearchTranslation:
    matched_source: str
    comparable_value: str


SearchTranslationStatus = Literal["provider", "gemini", "gloss_fallback", "missing"]
SearchTranslationReason = Literal[
    "provider_ok",
    "provider_self_translation",
    "gemini_ok",
    "gemini_missing",
    "gemini_self_translation",
    "gloss_fallback_used",
]


@dataclass(frozen=True, slots=True)
class SearchTranslationCandidate:
    translation: str | None
    invalid: InvalidSearchTranslation | None


@dataclass(frozen=True, slots=True)
class SearchTranslationDecision:
    lemma_translation: str | None
    saveable_translation: str | None
    lemma_translation_provider: str | None
    lemma_translation_status: SearchTranslationStatus
    lemma_translation_reason: SearchTranslationReason | None


def comparable_search_translation_key(value: str | None) -> str:
    normalized = normalize_token(value or "")
    if not normalized:
        return ""
    tokens = normalized.split(" ")
    while tokens and tokens[0] in _SELF_TRANSLATION_HELPER_PREFIXES:
        tokens = tokens[1:]
    return " ".join(tokens)


@lru_cache(maxsize=1)
def _english_verb_lemmas() -> frozenset[str]:
    path = BASE_DIR / "resources" / "dictionaries" / "english_wiki.jsonl"
    if not path.exists():
        return frozenset()

    lemmas: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if payload.get("lang_code") != "en" or payload.get("pos") != "verb":
                continue
            lemma = normalize_token(str(payload.get("word") or ""))
            if lemma:
                lemmas.add(lemma)
    return frozenset(lemmas)


def should_allow_identical_glossless_verb_translation(
    *,
    translation: str | None,
    lemma: str,
    pos_tag: str | None,
    gloss: str | None,
    frame_text: str | None,
) -> bool:
    if (pos_tag or "").strip().upper() != "VERB":
        return False
    if normalize_token(gloss or ""):
        return False

    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        return False
    if comparable_search_translation_key(translation) != normalized_lemma:
        return False
    if comparable_search_translation_key(frame_text) != normalized_lemma:
        return False

    return normalized_lemma in _english_verb_lemmas()


def invalid_search_translation(
    *,
    translation: str | None,
    lemma: str,
    surface_form: str | None = None,
    frame_text: str | None = None,
) -> InvalidSearchTranslation | None:
    comparable_translation = comparable_search_translation_key(translation)
    if not comparable_translation:
        return None

    candidates = (
        ("lemma", lemma),
        ("surface_form", surface_form),
        ("frame_text", frame_text),
    )
    for matched_source, source_value in candidates:
        comparable_source = comparable_search_translation_key(source_value)
        if comparable_source and comparable_translation == comparable_source:
            return InvalidSearchTranslation(
                matched_source=matched_source,
                comparable_value=comparable_translation,
            )
    return None


def evaluate_search_translation_candidate(
    *,
    translation: str | None,
    lemma: str,
    surface_form: str | None = None,
    frame_text: str | None = None,
) -> SearchTranslationCandidate:
    return SearchTranslationCandidate(
        translation=translation,
        invalid=invalid_search_translation(
            translation=translation,
            lemma=lemma,
            surface_form=surface_form,
            frame_text=frame_text,
        ),
    )


def build_search_translation_decision(
    *,
    provider_candidate: SearchTranslationCandidate,
    provider_name: str | None,
    contextual_candidate: SearchTranslationCandidate | None = None,
    contextual_provider_name: str | None = None,
    contextual_attempted: bool = False,
    gloss_fallback: str | None = None,
) -> SearchTranslationDecision:
    normalized_gloss_fallback = normalize_token(gloss_fallback or "") or None

    if contextual_attempted and contextual_candidate is not None:
        contextual_translation = normalize_token(contextual_candidate.translation or "") or None
        if contextual_translation:
            return SearchTranslationDecision(
                lemma_translation=contextual_translation,
                saveable_translation=contextual_translation,
                lemma_translation_provider=contextual_provider_name,
                lemma_translation_status="gemini",
                lemma_translation_reason="gemini_ok",
            )

    if provider_candidate.invalid is None:
        provider_translation = normalize_token(provider_candidate.translation or "") or None
        if provider_translation:
            return SearchTranslationDecision(
                lemma_translation=provider_translation,
                saveable_translation=provider_translation,
                lemma_translation_provider=provider_name,
                lemma_translation_status="provider",
                lemma_translation_reason="provider_ok",
            )

    if normalized_gloss_fallback:
        return SearchTranslationDecision(
            lemma_translation=None,
            saveable_translation=normalized_gloss_fallback,
            lemma_translation_provider=provider_name,
            lemma_translation_status="gloss_fallback",
            lemma_translation_reason="gloss_fallback_used",
        )

    if contextual_attempted and contextual_candidate is not None:
        return SearchTranslationDecision(
            lemma_translation=None,
            saveable_translation=None,
            lemma_translation_provider=None,
            lemma_translation_status="missing",
            lemma_translation_reason=(
                "gemini_self_translation"
                if contextual_candidate.invalid is not None
                else "gemini_missing"
            ),
        )

    if provider_candidate.invalid is not None:
        return SearchTranslationDecision(
            lemma_translation=None,
            saveable_translation=None,
            lemma_translation_provider=None,
            lemma_translation_status="missing",
            lemma_translation_reason="provider_self_translation",
        )

    return SearchTranslationDecision(
        lemma_translation=None,
        saveable_translation=None,
        lemma_translation_provider=None,
        lemma_translation_status="missing",
        lemma_translation_reason=None,
    )

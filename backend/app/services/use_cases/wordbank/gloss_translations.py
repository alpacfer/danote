from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.token_classifier import normalize_token

if TYPE_CHECKING:
    from app.services.cor_local import CORLocalEntry
    from app.services.use_cases.wordbank.runtime import WordbankRuntime

_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")
GlossTranslationCacheKey = tuple[str, str, str | None, str | None, str, str | None, str | None]


def is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    return _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is not None


def gloss_translation(
    runtime: WordbankRuntime,
    *,
    cor_entry: CORLocalEntry | None,
    gloss: str | None,
    lemma_translation: str | None,
    cache: dict[GlossTranslationCacheKey, str | None] | None = None,
) -> str | None:
    normalized_gloss = normalize_token(gloss or "")
    normalized_lemma_translation = normalize_token(lemma_translation or "")
    if not normalized_gloss:
        return None
    if normalized_lemma_translation and normalized_gloss == normalized_lemma_translation:
        return normalized_gloss
    if cor_entry is not None:
        translated = runtime.cor.lookup_translation_for_cor_gloss(
            entry=cor_entry,
            lemma_translation=lemma_translation,
            cache=cache if cache is not None else {},
        )
        normalized_translated = normalize_token(translated or "") or None
        if normalized_translated and normalized_translated != normalized_gloss:
            return normalized_translated
        if normalized_translated and is_likely_english_gloss(normalized_gloss):
            return normalized_translated
    if is_likely_english_gloss(normalized_gloss):
        return normalized_gloss
    return None


def meaning_gloss_translation(
    runtime: WordbankRuntime,
    *,
    lexeme_lemma: str,
    lexeme_pos_tag: str | None,
    meaning_gloss: str | None,
    meaning_translation: str | None,
    meaning_pos_tag: str | None,
    cor_lemma_idx: int | None,
    cache: dict[GlossTranslationCacheKey, str | None],
) -> str | None:
    normalized_meaning_gloss = normalize_token(meaning_gloss or "")
    normalized_meaning_translation = normalize_token(meaning_translation or "")
    if normalized_meaning_gloss and normalized_meaning_translation and normalized_meaning_gloss == normalized_meaning_translation:
        return normalized_meaning_gloss
    if cor_lemma_idx is None:
        return normalize_token(meaning_gloss or "") if is_likely_english_gloss(meaning_gloss) else None
    cor_entry = runtime.cor.best_cor_local_lemma_entry(
        lemma_idx=cor_lemma_idx,
        lemma=lexeme_lemma,
        preferred_pos_tag=meaning_pos_tag or lexeme_pos_tag,
    )
    return gloss_translation(
        runtime,
        cor_entry=cor_entry,
        gloss=meaning_gloss,
        lemma_translation=meaning_translation,
        cache=cache,
    )

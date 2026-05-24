from __future__ import annotations

import re
from typing import TYPE_CHECKING

from app.services.token_classifier import normalize_token

if TYPE_CHECKING:
    from app.services.cor_local import CORLocalEntry
    from app.services.use_cases.wordbank.runtime import WordbankRuntime

_LIKELY_ENGLISH_GLOSS_RE = re.compile(r"^[A-Za-z][A-Za-z ',-]*$")
# Common Danish function words that are pure ASCII. Any of them appearing in
# the gloss is a strong signal the phrase is Danish despite passing the
# ASCII-only regex. Sense-discovery glosses are always Danish — they read like
# 'stykke papir eller pap brugt til spil' for ``kort``, which has no æ/ø/å but
# is unmistakably Danish thanks to ``eller`` and ``til``. Without this guard
# the regex misidentifies the phrase as English and the wordbank header renders
# 'playing card (stykke papir eller pap brugt til spil)'.
_DANISH_GLOSS_STOPWORDS = frozenset({
    "af", "at", "den", "der", "det", "eller", "en", "er", "et", "for", "fra",
    "har", "hvor", "i", "ikke", "ind", "kan", "med", "ned", "noget", "nogen",
    "om", "op", "over", "pa", "samme", "sin", "som", "til", "ud", "ved", "og",
})
GlossTranslationCacheKey = tuple[str, str, str | None, str | None, str, str | None, str | None]


def _ascii_fold(value: str) -> str:
    return (
        value.replace("æ", "ae").replace("ø", "o").replace("å", "a")
        .replace("Æ", "ae").replace("Ø", "o").replace("Å", "a")
    )


def is_likely_english_gloss(gloss: str | None) -> bool:
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return False
    if _LIKELY_ENGLISH_GLOSS_RE.fullmatch(normalized_gloss) is None:
        return False
    folded_tokens = {_ascii_fold(token.lower()) for token in normalized_gloss.split()}
    if folded_tokens & _DANISH_GLOSS_STOPWORDS:
        return False
    return True


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
    if _is_redundant_gloss_translation(
        normalized_gloss,
        normalized_lemma_translation,
        pos_tag=cor_entry.pos_tag if cor_entry is not None else None,
    ):
        return None
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
    meaning_english_gloss: str | None = None,
) -> str | None:
    # Sense-discovery saves persist an English gloss directly on the meaning
    # row (lexeme_meanings.english_gloss). That's the authoritative source —
    # no need to round-trip through COR lookups or the ASCII-only English
    # heuristic, which used to misclassify Danish glosses without æ/ø/å as
    # English and echo them verbatim into the wordbank header. Fall through
    # to the COR-translation pipeline only when the meaning doesn't carry
    # an english_gloss (legacy rows + nouns whose meaning came straight from
    # COR without sense fan-out).
    normalized_english_gloss = normalize_token(meaning_english_gloss or "")
    if normalized_english_gloss:
        normalized_meaning_translation = normalize_token(meaning_translation or "")
        if _is_redundant_gloss_translation(
            normalized_english_gloss,
            normalized_meaning_translation,
            pos_tag=meaning_pos_tag or lexeme_pos_tag,
        ):
            return None
        return normalized_english_gloss

    normalized_meaning_gloss = normalize_token(meaning_gloss or "")
    normalized_meaning_translation = normalize_token(meaning_translation or "")
    if _is_redundant_gloss_translation(
        normalized_meaning_gloss,
        normalized_meaning_translation,
        pos_tag=meaning_pos_tag or lexeme_pos_tag,
    ):
        return None
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


def _is_redundant_gloss_translation(
    normalized_gloss_translation: str,
    normalized_lemma_translation: str,
    *,
    pos_tag: str | None,
) -> bool:
    if not normalized_gloss_translation or not normalized_lemma_translation:
        return False
    if normalized_gloss_translation == normalized_lemma_translation:
        return True
    if (pos_tag or "").upper() != "VERB":
        return False
    infinitive = normalized_lemma_translation.removeprefix("to ").strip()
    return (
        infinitive == normalized_gloss_translation
        or infinitive.startswith(f"{normalized_gloss_translation} ")
    )

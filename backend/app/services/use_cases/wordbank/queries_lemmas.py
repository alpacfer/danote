from __future__ import annotations

from app.api.schemas.v1.wordbank import (
    LemmaListResponse,
    LemmaSummary,
    WordbankSearchItem,
    WordbankSearchResponse,
)
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def list_lemmas(runtime: WordbankRuntime) -> LemmaListResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    rows = runtime.repository.list_lemmas()

    return LemmaListResponse(
        items=[
            LemmaSummary(
                lemma=row.lemma,
                display_lemma=_display_lemma_for_list(runtime, row.lemma, row.pos_tag),
                english_translation=row.english_translation,
                variation_count=row.variation_count,
            )
            for row in rows
        ]
    )


def search_lemmas(runtime: WordbankRuntime, query: str, *, limit: int = 8) -> WordbankSearchResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    normalized_query = normalize_token(query)
    if not normalized_query:
        raise ValueError("query is required")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    rows = runtime.repository.search_lemmas(normalized_query, limit=limit)

    return WordbankSearchResponse(
        items=[
            WordbankSearchItem(
                lemma=row.lemma,
                display_lemma=_display_lemma_for_list(runtime, row.lemma, row.pos_tag),
                meaning_id=row.meaning_id,
                meaning_key=row.meaning_key,
                gloss=row.gloss,
                cor_lemma_idx=row.cor_lemma_idx,
                english_translation=row.english_translation,
                variation_count=row.variation_count,
                match_surface=row.match_surface,
                query_cor_ids=row.query_cor_ids,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
            )
            for row in rows
        ]
    )


def _display_lemma_for_list(runtime: WordbankRuntime, lemma: str, pos_tag: str | None) -> str:
    if pos_tag is None:
        pos_tag, _morphology = runtime.nlp.extract_pos_and_morphology(lemma)
    if pos_tag in {"VERB", "AUX"}:
        return f"at {lemma}"
    return lemma

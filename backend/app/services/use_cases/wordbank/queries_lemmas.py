from __future__ import annotations

from app.api.schemas.v1.wordbank import (
    LemmaListResponse,
    LemmaSummary,
    WordbankSearchItem,
    WordbankSearchResponse,
)
from app.services.fuzzy_search import fuzzy_suggest
from app.services.token_classifier import normalize_token
from app.services.use_cases.static_builtin_words import static_builtin_senses_for_token
from app.services.use_cases.static_hv_words import (
    StaticHvWord,
    static_hv_word_for_english,
    static_hv_word_for_token,
)
from app.services.use_cases.static_presaved_words import (
    StaticPresavedWord,
    static_presaved_word_for_english,
    static_presaved_word_for_token,
)
from app.services.use_cases.static_pronouns import (
    StaticPronoun,
    static_pronoun_for_english,
    static_pronoun_for_token,
)
from app.services.use_cases.wordbank.gloss_translations import meaning_gloss_translation
from app.services.use_cases.wordbank.meaning_sections import ensure_wordbank_meaning_compatibility
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def list_lemmas(runtime: WordbankRuntime) -> LemmaListResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    rows = [
        row
        for row in runtime.repository.list_lemmas()
        if not static_builtin_senses_for_token(row.lemma)
        and static_pronoun_for_token(row.lemma) is None
        and static_hv_word_for_token(row.lemma) is None
    ]

    return LemmaListResponse(
        items=[
            LemmaSummary(
                lemma=row.lemma,
                display_lemma=_display_lemma_for_list(runtime, row.lemma, row.pos_tag),
                english_translation=row.english_translation,
                pos_tags=list(row.pos_tags),
                categories=list(row.categories),
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

    static_hv_word = static_hv_word_for_token(normalized_query)
    if static_hv_word is not None:
        return _static_hv_word_search_response(static_hv_word, match_surface=None)
    static_english_hv_word = static_hv_word_for_english(query)
    if static_english_hv_word is not None:
        return _static_hv_word_search_response(static_english_hv_word, match_surface=normalized_query)

    static_pronoun = static_pronoun_for_token(normalized_query)
    if static_pronoun is not None:
        return _static_pronoun_search_response(static_pronoun, match_surface=None)
    static_english_pronoun = static_pronoun_for_english(query)
    if static_english_pronoun is not None:
        return _static_pronoun_search_response(static_english_pronoun, match_surface=normalized_query)

    static_presaved_word = static_presaved_word_for_token(normalized_query)
    if static_presaved_word is not None:
        return _static_presaved_word_search_response(static_presaved_word, match_surface=None)
    static_english_presaved_word = static_presaved_word_for_english(query)
    if static_english_presaved_word is not None:
        return _static_presaved_word_search_response(static_english_presaved_word, match_surface=normalized_query)

    rows = runtime.repository.search_lemmas(normalized_query, limit=limit)

    did_you_mean: str | None = None
    if not rows:
        all_lemmas = runtime.repository.list_all_lemma_strings()
        suggestions = fuzzy_suggest(normalized_query, all_lemmas)
        if suggestions:
            did_you_mean = suggestions[0]
            rows = runtime.repository.search_lemmas(did_you_mean, limit=limit)

    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}

    return WordbankSearchResponse(
        did_you_mean=did_you_mean,
        items=[
            WordbankSearchItem(
                lemma=row.lemma,
                display_lemma=_display_lemma_for_list(runtime, row.lemma, row.pos_tag),
                meaning_id=row.meaning_id,
                meaning_key=row.meaning_key,
                gloss=row.gloss,
                gloss_translation=(
                    meaning_gloss_translation(
                        runtime,
                        lexeme_lemma=row.lemma,
                        lexeme_pos_tag=row.pos_tag,
                        meaning_gloss=row.gloss,
                        meaning_translation=row.english_translation,
                        meaning_pos_tag=row.pos_tag,
                        cor_lemma_idx=row.cor_lemma_idx,
                        cache=gloss_translation_cache,
                        meaning_english_gloss=row.english_gloss,
                    )
                    if row.meaning_id is not None
                    else None
                ),
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


def _static_hv_word_search_response(
    hv_word: StaticHvWord,
    *,
    match_surface: str | None,
) -> WordbankSearchResponse:
    return WordbankSearchResponse(
        did_you_mean=None,
        items=[
            WordbankSearchItem(
                lemma=hv_word.lemma,
                display_lemma=hv_word.lemma,
                meaning_id=None,
                meaning_key=None,
                gloss=None,
                gloss_translation=None,
                cor_lemma_idx=None,
                english_translation=hv_word.english_translation,
                variation_count=1,
                match_surface=match_surface,
                query_cor_ids=[],
                pos_tag=hv_word.pos_tag,
                morphology=hv_word.morphology,
            )
        ],
    )


def _static_pronoun_search_response(
    pronoun: StaticPronoun,
    *,
    match_surface: str | None,
) -> WordbankSearchResponse:
    return WordbankSearchResponse(
        did_you_mean=None,
        items=[
            WordbankSearchItem(
                lemma=pronoun.lemma,
                display_lemma=pronoun.lemma,
                meaning_id=None,
                meaning_key=None,
                gloss=None,
                gloss_translation=None,
                cor_lemma_idx=None,
                english_translation=pronoun.english_translation,
                variation_count=1,
                match_surface=match_surface,
                query_cor_ids=[],
                pos_tag=pronoun.pos_tag,
                morphology=pronoun.morphology,
            )
        ],
    )


def _static_presaved_word_search_response(
    word: StaticPresavedWord,
    *,
    match_surface: str | None,
) -> WordbankSearchResponse:
    return WordbankSearchResponse(
        did_you_mean=None,
        items=[
            WordbankSearchItem(
                lemma=word.lemma,
                display_lemma=word.lemma,
                meaning_id=None,
                meaning_key=None,
                gloss=None,
                gloss_translation=None,
                cor_lemma_idx=None,
                english_translation=word.english_translation,
                variation_count=1,
                match_surface=match_surface,
                query_cor_ids=[],
                pos_tag=word.pos_tag,
                morphology=word.morphology,
            )
        ],
    )


def _display_lemma_for_list(runtime: WordbankRuntime, lemma: str, pos_tag: str | None) -> str:
    if pos_tag is None:
        pos_tag, _morphology = runtime.nlp.extract_pos_and_morphology(lemma)
    if pos_tag in {"VERB", "AUX"}:
        return f"at {lemma}"
    return lemma

from __future__ import annotations

from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import ResolveQueryResponse, WordActionSuggestion
from app.db.migrations import get_connection
from app.nlp.token_filter import is_short_letter_word
from app.services.en_local import ENLocalLexiconService
from app.services.text_preprocessing import strip_inline_comments
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.translation import TranslationService
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
from app.services.use_cases.wordbank.collaborators.cor_actions import (
    build_cor_add_options,
    find_saved_lemma,
    replace_danish_add_actions,
)
from app.services.use_cases.wordbank.collaborators.en_resolution import resolve_en_query
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.shared import build_word_action_suggestions


def resolve_query(
    *,
    db_path: Path,
    translation: TranslationCollaborator,
    nlp: NLPCollaborator,
    owner_user_id: int = 1,
    cor_entries_lookup,
    query_text: str,
    include_translations: bool = True,
    include_language_detection: bool = True,
    en_local_lexicon_service: ENLocalLexiconService | None = None,
    en_gemini_translation_service=None,
    translation_service: TranslationService | None = None,
) -> ResolveQueryResponse:
    query_without_comments = strip_inline_comments(query_text)
    normalized_query = normalize_token(query_without_comments)
    if not normalized_query:
        raise ValueError("query_text is required")

    static_hv_word = static_hv_word_for_token(normalized_query)
    if static_hv_word is not None:
        return static_hv_word_resolve_response(normalized_query, static_hv_word, language="da")

    static_english_hv_word = static_hv_word_for_english(query_without_comments)
    if static_english_hv_word is not None:
        return static_hv_word_resolve_response(
            normalized_query,
            static_english_hv_word,
            language="en",
        )

    static_pronoun = static_pronoun_for_token(normalized_query)
    if static_pronoun is not None:
        return static_pronoun_resolve_response(normalized_query, static_pronoun, language="da")

    static_english_pronoun = static_pronoun_for_english(query_without_comments)
    if static_english_pronoun is not None:
        return static_pronoun_resolve_response(
            normalized_query,
            static_english_pronoun,
            language="en",
        )

    static_presaved_word = static_presaved_word_for_token(normalized_query)
    if static_presaved_word is not None:
        return static_presaved_word_resolve_response(normalized_query, static_presaved_word, language="da")

    static_english_presaved_word = static_presaved_word_for_english(query_without_comments)
    if static_english_presaved_word is not None:
        return static_presaved_word_resolve_response(
            normalized_query,
            static_english_presaved_word,
            language="en",
        )

    en_query_response: ResolveQueryResponse | None = None
    has_en_local_match = (
        en_local_lexicon_service is not None
        and en_local_lexicon_service.has_form(normalized_query)
    )
    if has_en_local_match and en_local_lexicon_service is not None:
        en_query_response = resolve_en_query(
            normalized_query=normalized_query,
            en_local_lexicon_service=en_local_lexicon_service,
            en_gemini_translation_service=en_gemini_translation_service,
            translation_service=translation_service,
            include_translations=include_translations,
        )
        if not cor_entries_lookup(normalized_query):
            return en_query_response

    if is_short_letter_word(normalized_query):
        return ResolveQueryResponse(
            query_surface=normalized_query,
            query_lemma=None,
            classification="uncertain",
            matched_lemma=None,
            matched_lemma_summary=None,
            query_pos_tag=None,
            query_morphology=None,
            resolved_surface=normalized_query,
            resolved_lemma=None,
            da_to_en_translation=None,
            en_to_da_translation=None,
            en_to_da_lemma=None,
            en_to_da_pos_tag=None,
            en_to_da_morphology=None,
            query_language=None,
            query_language_confidence=None,
            word_actions=[],
            en_pos_groups=en_query_response.en_pos_groups if en_query_response is not None else [],
        )

    is_at_verb_search = False
    classifier_query = normalized_query
    if normalized_query.startswith("at ") and len(normalized_query) > 3:
        verb_candidate = normalized_query[3:].strip()
        if " " not in verb_candidate:
            try:
                candidate_entries = cor_entries_lookup(verb_candidate)
                if any(getattr(e, "pos_tag", None) == "VERB" for e in candidate_entries):
                    is_at_verb_search = True
                    classifier_query = verb_candidate
            except Exception:
                pass

    classifier = LemmaAwareClassifier(
        db_path,
        nlp_adapter=None,
        owner_user_id=owner_user_id,
    )
    token = classifier.classify(classifier_query)

    if is_at_verb_search:
        import dataclasses
        token = dataclasses.replace(
            token,
            surface_token=query_without_comments,
            normalized_token=normalized_query,
            lemma_candidate=token.lemma_candidate or classifier_query,
        )

    cor_add_options = build_cor_add_options(
        normalized_query,
        include_translations=include_translations,
        cor_entries_lookup=cor_entries_lookup,
        translation=translation,
        db_path=db_path,
        owner_user_id=owner_user_id,
    )
    preferred_pos_tag = cor_add_options[0].pos_tag if cor_add_options else None
    query_pos_tag, query_morphology = nlp.extract_pos_and_morphology(
        normalized_query,
        preferred_pos_tag=preferred_pos_tag,
    )

    classification = token.classification
    query_lemma = token.lemma_candidate
    matched_lemma = token.matched_lemma
    if cor_add_options and not query_lemma:
        query_lemma = cor_add_options[0].lemma

    if token.match_source == "none" and cor_add_options:
        saved_lemma = find_saved_lemma(
            db_path,
            [option.lemma for option in cor_add_options],
            owner_user_id=owner_user_id,
        )
        if saved_lemma:
            classification = "variation"
            matched_lemma = saved_lemma
            query_lemma = query_lemma or saved_lemma

    matched_lemma_summary = load_matched_lemma_summary(
        db_path,
        matched_lemma,
        owner_user_id=owner_user_id,
    )

    resolved_surface = token.normalized_token or normalized_query
    resolved_lemma = query_lemma
    da_to_en_translation: str | None = None
    en_to_da_translation: str | None = None
    en_to_da_lemma: str | None = None
    en_to_da_pos_tag: str | None = None
    en_to_da_morphology: str | None = None
    query_language: Literal["en", "da", "ambiguous"] | None = None
    query_language_confidence: float | None = None

    if include_translations:
        translated = translation.lookup_translation(normalized_query)
        if translated:
            normalized_translation = normalize_token(translated)
            if translation.normalize_comparable(
                normalized_translation
            ) != translation.normalize_comparable(normalized_query):
                da_to_en_translation = normalized_translation
        if da_to_en_translation is None:
            for option in cor_add_options:
                if option.translation_label:
                    da_to_en_translation = option.translation_label
                    break

        reverse_translated = translation.lookup_reverse_translation(normalized_query)
        if reverse_translated:
            normalized_reverse = normalize_token(reverse_translated)
            if translation.normalize_comparable(
                normalized_reverse
            ) != translation.normalize_comparable(normalized_query):
                en_to_da_translation = normalized_reverse

        if en_to_da_translation:
            en_to_da_pos_tag, en_to_da_morphology = nlp.extract_pos_and_morphology(
                en_to_da_translation
            )
            translated_classification = classifier.classify(en_to_da_translation)
            en_to_da_lemma = (
                translated_classification.matched_lemma
                or translated_classification.lemma_candidate
            )

    if include_language_detection:
        detected = translation.detect_word_language(
            normalized_query,
            cor_entries_lookup=cor_entries_lookup,
        )
        query_language = detected.language
        query_language_confidence = max(0.0, min(1.0, float(detected.confidence)))
    if cor_add_options:
        query_language = "da"
        query_language_confidence = max(float(query_language_confidence or 0.0), 0.95)

    if (
        token.match_source == "none"
        and not cor_add_options
        and en_to_da_translation
        and (
            query_language == "en"
            or (
                query_language != "da"
                and translation.is_likely_english_word(normalized_query)
            )
            or not resolved_lemma
            or translation.normalize_comparable(resolved_lemma)
            == translation.normalize_comparable(normalized_query)
        )
    ):
        resolved_surface = en_to_da_translation
        resolved_lemma = en_to_da_translation

    word_actions = build_word_action_suggestions(
        classification=classification,
        query_surface=token.normalized_token or normalized_query,
        query_lemma=query_lemma,
        query_pos_tag=query_pos_tag,
        query_morphology=query_morphology,
        matched_lemma=matched_lemma,
        da_to_en_translation=da_to_en_translation,
        en_to_da_translation=en_to_da_translation,
        en_to_da_lemma=en_to_da_lemma,
        en_to_da_pos_tag=en_to_da_pos_tag,
        en_to_da_morphology=en_to_da_morphology,
        query_language=query_language,
        query_language_confidence=query_language_confidence,
    )
    word_actions = replace_danish_add_actions(
        word_actions,
        classification=classification,
        matched_lemma=matched_lemma,
        cor_add_options=cor_add_options,
        fallback_translation=da_to_en_translation,
    )

    return ResolveQueryResponse(
        query_surface=token.normalized_token or normalized_query,
        query_lemma=query_lemma,
        classification=classification,
        matched_lemma=matched_lemma,
        matched_lemma_summary=matched_lemma_summary,
        query_pos_tag=query_pos_tag,
        query_morphology=query_morphology,
        resolved_surface=resolved_surface,
        resolved_lemma=resolved_lemma,
        da_to_en_translation=da_to_en_translation,
        en_to_da_translation=en_to_da_translation,
        en_to_da_lemma=en_to_da_lemma,
        en_to_da_pos_tag=en_to_da_pos_tag,
        en_to_da_morphology=en_to_da_morphology,
        query_language=query_language,
        query_language_confidence=query_language_confidence,
        word_actions=word_actions,
        en_pos_groups=en_query_response.en_pos_groups if en_query_response is not None else [],
    )


def static_hv_word_resolve_response(
    query: str,
    hv_word: StaticHvWord,
    *,
    language: Literal["da", "en"],
) -> ResolveQueryResponse:
    is_english = language == "en"
    return ResolveQueryResponse(
        query_surface=query,
        query_lemma=hv_word.lemma,
        classification="known",
        matched_lemma=hv_word.lemma,
        matched_lemma_summary=None,
        query_pos_tag=hv_word.pos_tag,
        query_morphology=hv_word.morphology,
        resolved_surface=hv_word.lemma,
        resolved_lemma=hv_word.lemma,
        da_to_en_translation=None if is_english else hv_word.english_translation,
        en_to_da_translation=hv_word.lemma if is_english else None,
        en_to_da_lemma=hv_word.lemma if is_english else None,
        en_to_da_pos_tag=hv_word.pos_tag if is_english else None,
        en_to_da_morphology=hv_word.morphology if is_english else None,
        query_language=language,
        query_language_confidence=1.0,
        word_actions=[
            WordActionSuggestion(
                action_type="open_wordbank",
                surface=hv_word.lemma,
                lemma=hv_word.lemma,
                translation_label=hv_word.english_translation,
                direction="known",
                direction_label="Wordbank",
                pos_tag=hv_word.pos_tag,
                morphology=hv_word.morphology,
            )
        ],
        en_pos_groups=[],
    )


def static_pronoun_resolve_response(
    query: str,
    pronoun: StaticPronoun,
    *,
    language: Literal["da", "en"],
) -> ResolveQueryResponse:
    is_english = language == "en"
    return ResolveQueryResponse(
        query_surface=query,
        query_lemma=pronoun.lemma,
        classification="known",
        matched_lemma=pronoun.lemma,
        matched_lemma_summary=None,
        query_pos_tag=pronoun.pos_tag,
        query_morphology=pronoun.morphology,
        resolved_surface=pronoun.lemma,
        resolved_lemma=pronoun.lemma,
        da_to_en_translation=None if is_english else pronoun.english_translation,
        en_to_da_translation=pronoun.lemma if is_english else None,
        en_to_da_lemma=pronoun.lemma if is_english else None,
        en_to_da_pos_tag=pronoun.pos_tag if is_english else None,
        en_to_da_morphology=pronoun.morphology if is_english else None,
        query_language=language,
        query_language_confidence=1.0,
        word_actions=[
            WordActionSuggestion(
                action_type="open_wordbank",
                surface=pronoun.lemma,
                lemma=pronoun.lemma,
                translation_label=pronoun.english_translation,
                direction="known",
                direction_label="Wordbank",
                pos_tag=pronoun.pos_tag,
                morphology=pronoun.morphology,
            )
        ],
        en_pos_groups=[],
    )


def static_presaved_word_resolve_response(
    query: str,
    word: StaticPresavedWord,
    *,
    language: Literal["da", "en"],
) -> ResolveQueryResponse:
    is_english = language == "en"
    return ResolveQueryResponse(
        query_surface=query,
        query_lemma=word.lemma,
        classification="known",
        matched_lemma=word.lemma,
        matched_lemma_summary=None,
        query_pos_tag=word.pos_tag,
        query_morphology=word.morphology,
        resolved_surface=word.lemma,
        resolved_lemma=word.lemma,
        da_to_en_translation=None if is_english else word.english_translation,
        en_to_da_translation=word.lemma if is_english else None,
        en_to_da_lemma=word.lemma if is_english else None,
        en_to_da_pos_tag=word.pos_tag if is_english else None,
        en_to_da_morphology=word.morphology if is_english else None,
        query_language=language,
        query_language_confidence=1.0,
        word_actions=[
            WordActionSuggestion(
                action_type="open_wordbank",
                surface=word.lemma,
                lemma=word.lemma,
                translation_label=word.english_translation,
                direction="known",
                direction_label="Wordbank",
                pos_tag=word.pos_tag,
                morphology=word.morphology,
            )
        ],
        en_pos_groups=[],
    )


def load_matched_lemma_summary(
    db_path: Path,
    matched_lemma: str | None,
    *,
    owner_user_id: int = 1,
) -> ResolveQueryResponse.MatchedLemmaSummary | None:
    if not matched_lemma:
        return None

    with get_connection(db_path) as conn:
        lemma_row = conn.execute(
            """
            WITH meaning_counts AS (
                SELECT lexeme_id, COUNT(*) AS meaning_count
                FROM lexeme_meanings
                GROUP BY lexeme_id
            ),
            single_meanings AS (
                SELECT lexeme_id, english_translation
                FROM lexeme_meanings
                GROUP BY lexeme_id
                HAVING COUNT(*) = 1
            )
            SELECT
                l.lemma,
                CASE
                    WHEN COALESCE(mc.meaning_count, 0) = 0 THEN l.english_translation
                    WHEN mc.meaning_count = 1 THEN COALESCE(sm.english_translation, l.english_translation)
                    ELSE NULL
                END AS english_translation,
                COUNT(DISTINCT CASE WHEN sf.form <> l.lemma THEN sf.form END) AS variation_count
            FROM lexemes l
            LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
            LEFT JOIN meaning_counts mc ON mc.lexeme_id = l.id
            LEFT JOIN single_meanings sm ON sm.lexeme_id = l.id
            WHERE l.owner_user_id = ? AND l.lemma = ?
            GROUP BY l.id
            LIMIT 1
            """,
            (owner_user_id, matched_lemma),
        ).fetchone()
    if lemma_row is None:
        return None

    return ResolveQueryResponse.MatchedLemmaSummary(
        lemma=lemma_row["lemma"],
        english_translation=lemma_row["english_translation"],
        variation_count=lemma_row["variation_count"],
    )

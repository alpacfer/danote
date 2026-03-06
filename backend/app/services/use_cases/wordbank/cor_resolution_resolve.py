from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.wordbank import ResolveQueryResponse
from app.db.migrations import get_connection
from app.nlp.token_filter import is_short_letter_word
from app.services.text_preprocessing import strip_inline_comments
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.use_cases.wordbank.shared import build_word_action_suggestions


class WordbankCorResolutionResolveMixin:
    def resolve_query(
        self,
        query_text: str,
        *,
        include_translations: bool = True,
        include_language_detection: bool = True,
    ) -> ResolveQueryResponse:
        query_without_comments = strip_inline_comments(query_text)
        normalized_query = normalize_token(query_without_comments)
        if not normalized_query:
            raise ValueError("query_text is required")

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
            )

        classifier = LemmaAwareClassifier(
            self._db_path,
            nlp_adapter=None,
            typo_engine=self._typo_engine,
        )
        token = classifier.classify(normalized_query)
        cor_add_options = self._build_cor_add_options(
            normalized_query,
            include_translations=include_translations,
        )
        preferred_pos_tag = cor_add_options[0].pos_tag if cor_add_options else None
        query_pos_tag, query_morphology = self._extract_pos_and_morphology(
            normalized_query,
            preferred_pos_tag=preferred_pos_tag,
        )

        classification = token.classification
        query_lemma = token.lemma_candidate
        matched_lemma = token.matched_lemma
        if cor_add_options and not query_lemma:
            query_lemma = cor_add_options[0].lemma

        if token.match_source == "none" and cor_add_options:
            saved_lemma = self._find_saved_lemma([option.lemma for option in cor_add_options])
            if saved_lemma:
                classification = "variation"
                matched_lemma = saved_lemma
                query_lemma = query_lemma or saved_lemma

        matched_lemma_summary: ResolveQueryResponse.MatchedLemmaSummary | None = None
        if matched_lemma:
            with get_connection(self._db_path) as conn:
                lemma_row = conn.execute(
                    """
                    SELECT l.lemma, l.english_translation, COUNT(sf.id) AS variation_count
                    FROM lexemes l
                    LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                    WHERE l.lemma = ?
                    GROUP BY l.id
                    LIMIT 1
                    """,
                    (matched_lemma,),
                ).fetchone()
            if lemma_row is not None:
                matched_lemma_summary = ResolveQueryResponse.MatchedLemmaSummary(
                    lemma=lemma_row["lemma"],
                    english_translation=lemma_row["english_translation"],
                    variation_count=lemma_row["variation_count"],
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
            translated = self._lookup_translation(normalized_query)
            if translated:
                normalized_translation = normalize_token(translated)
                if self._normalize_comparable(normalized_translation) != self._normalize_comparable(normalized_query):
                    da_to_en_translation = normalized_translation
            if da_to_en_translation is None:
                for option in cor_add_options:
                    if option.translation_label:
                        da_to_en_translation = option.translation_label
                        break

            reverse_translated = self._lookup_reverse_translation(normalized_query)
            if reverse_translated:
                normalized_reverse = normalize_token(reverse_translated)
                if self._normalize_comparable(normalized_reverse) != self._normalize_comparable(normalized_query):
                    en_to_da_translation = normalized_reverse

            if en_to_da_translation:
                en_to_da_pos_tag, en_to_da_morphology = self._extract_pos_and_morphology(en_to_da_translation)
                translated_classification = classifier.classify(en_to_da_translation)
                en_to_da_lemma = translated_classification.matched_lemma or translated_classification.lemma_candidate

        if include_language_detection:
            detected = self.detect_word_language(normalized_query)
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
                or (query_language != "da" and self._is_likely_english_word(normalized_query))
                or not resolved_lemma
                or self._normalize_comparable(resolved_lemma) == self._normalize_comparable(normalized_query)
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
        word_actions = self._replace_danish_add_actions(
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
        )



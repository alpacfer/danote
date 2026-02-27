from __future__ import annotations

import sqlite3

from app.api.schemas.v1.analyze import AnalyzedToken
from app.nlp.adapter import NLPAdapter
from app.nlp.token_filter import is_wordlike_token
from app.services.token_classifier import LemmaAwareClassifier


class AnalyzeNoteUseCase:
    def __init__(self, db_path, nlp_adapter: NLPAdapter, typo_engine=None):
        self._db_path = db_path
        self._nlp_adapter = nlp_adapter
        self._typo_engine = typo_engine

    def execute(self, text: str) -> list[AnalyzedToken]:
        classifier = LemmaAwareClassifier(
            self._db_path,
            nlp_adapter=self._nlp_adapter,
            typo_engine=self._typo_engine,
        )

        filtered_nlp_tokens = []
        for nlp_token in self._nlp_adapter.tokenize(text):
            surface = nlp_token.text
            if not surface.strip():
                continue
            if nlp_token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            filtered_nlp_tokens.append(nlp_token)

        surfaces = [nlp_token.text for nlp_token in filtered_nlp_tokens]

        tokens: list[AnalyzedToken] = []
        try:
            for result, nlp_token in zip(
                classifier.classify_many(surfaces),
                filtered_nlp_tokens,
                strict=True,
            ):
                tokens.append(
                    AnalyzedToken(
                        surface_token=result.surface_token,
                        normalized_token=result.normalized_token,
                        lemma_candidate=result.lemma_candidate,
                        classification=result.classification,
                        match_source=result.match_source,
                        matched_lemma=result.matched_lemma,
                        matched_surface_form=result.matched_surface_form,
                        suggestions=[
                            {
                                "value": suggestion.value,
                                "score": suggestion.score,
                                "source_flags": list(suggestion.source_flags),
                            }
                            for suggestion in result.suggestions
                        ],
                        confidence=result.confidence,
                        reason_tags=list(result.reason_tags),
                        pos_tag=nlp_token.pos,
                        morphology=nlp_token.morphology,
                        status=result.classification,
                        surface=result.surface_token,
                        normalized=result.normalized_token,
                        lemma=result.matched_lemma or result.lemma_candidate,
                    )
                )
        except sqlite3.OperationalError:
            raise

        return tokens

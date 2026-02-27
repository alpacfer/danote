from __future__ import annotations

import sqlite3

from app.api.schemas.v1.analyze import AnalyzedToken
from app.nlp.adapter import NLPAdapter, NLPToken
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

        token_metadata: list[tuple[str, str | None, str | None]] = []
        for nlp_token in self._nlp_adapter.tokenize(text):
            surface = nlp_token.text
            if not surface.strip():
                continue
            if nlp_token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            token_metadata.append((surface, nlp_token.pos, nlp_token.morphology))

        surfaces = [surface for surface, _, _ in token_metadata]

        tokens: list[AnalyzedToken] = []
        try:
            for result, (_, pos_tag, morphology) in zip(
                classifier.classify_many(surfaces),
                token_metadata,
                strict=True,
            ):
                tokens.append(
                    AnalyzedToken(
                        surface_token=result.surface_token,
                        normalized_token=result.normalized_token,
                        lemma_candidate=result.lemma_candidate,
                        pos_tag=pos_tag,
                        morphology=morphology,
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
                        status=result.classification,
                        surface=result.surface_token,
                        normalized=result.normalized_token,
                        lemma=result.matched_lemma or result.lemma_candidate,
                        pos_tag=nlp_token.pos,
                        morphology=nlp_token.morphology,
                    )
                )
        except sqlite3.OperationalError:
            raise

        return tokens

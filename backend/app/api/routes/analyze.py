from __future__ import annotations

import logging
import sqlite3
from typing import Literal

from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Request

from app.nlp.token_filter import is_wordlike_token
from app.services.token_classifier import LemmaAwareClassifier

router = APIRouter()
logger = logging.getLogger(__name__)


class AnalyzeRequest(BaseModel):
    text: str = Field(...)


class AnalyzedToken(BaseModel):
    surface_token: str
    normalized_token: str
    lemma_candidate: str | None
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    match_source: Literal["exact", "lemma", "none"]
    matched_lemma: str | None
    matched_surface_form: str | None
    suggestions: list[dict[str, object]] = Field(default_factory=list)
    confidence: float = 0.0
    reason_tags: list[str] = Field(default_factory=list)

    # v1-friendly aliases
    status: Literal["known", "variation", "typo_likely", "uncertain", "new"]
    surface: str
    normalized: str
    lemma: str | None


class AnalyzeResponse(BaseModel):
    tokens: list[AnalyzedToken]


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_note(payload: AnalyzeRequest, request: Request) -> AnalyzeResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )
    if not bool(getattr(request.app.state, "nlp_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="NLP unavailable. Check backend logs and NLP model installation.",
        )

    settings = request.app.state.settings
    nlp_adapter = request.app.state.nlp_adapter
    if nlp_adapter is None:
        raise HTTPException(
            status_code=503,
            detail="NLP unavailable. Check backend logs and NLP model installation.",
        )
    classifier = LemmaAwareClassifier(
        settings.db_path,
        nlp_adapter=nlp_adapter,
        typo_engine=getattr(request.app.state, "typo_engine", None),
    )

    tokens: list[AnalyzedToken] = []
    try:
        surfaces: list[str] = []
        for nlp_token in nlp_adapter.tokenize(payload.text):
            surface = nlp_token.text
            if not surface.strip():
                continue
            if nlp_token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            surfaces.append(surface)

        for result in classifier.classify_many(surfaces):
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
                    status=result.classification,
                    surface=result.surface_token,
                    normalized=result.normalized_token,
                    lemma=result.matched_lemma or result.lemma_candidate,
                )
            )
    except sqlite3.OperationalError as exc:
        logger.exception("analyze_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return AnalyzeResponse(tokens=tokens)

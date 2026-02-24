from __future__ import annotations

import logging
import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field


router = APIRouter()
logger = logging.getLogger(__name__)


class TokenFeedbackRequest(BaseModel):
    raw_token: str = Field(..., min_length=1)
    predicted_status: str = Field(..., min_length=1)
    suggestions_shown: list[str] = Field(default_factory=list)
    user_action: Literal["replace", "ignore", "add_as_new", "dismiss"]
    chosen_value: str | None = None


class TokenFeedbackResponse(BaseModel):
    status: Literal["recorded"]


class TokenIgnoreRequest(BaseModel):
    token: str = Field(..., min_length=1)
    scope: Literal["session", "global"] = "global"
    expires_at: str | None = None


class TokenIgnoreResponse(BaseModel):
    status: Literal["ignored"]


@router.post("/tokens/feedback", response_model=TokenFeedbackResponse)
def post_token_feedback(payload: TokenFeedbackRequest, request: Request) -> TokenFeedbackResponse:
    engine = getattr(request.app.state, "typo_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Typo engine unavailable.")
    try:
        engine.add_feedback(
            raw_token=payload.raw_token,
            predicted_status=payload.predicted_status,
            suggestions_shown=payload.suggestions_shown,
            user_action=payload.user_action,
            chosen_value=payload.chosen_value,
        )
    except sqlite3.OperationalError as exc:
        logger.exception("token_feedback_db_operational_error")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return TokenFeedbackResponse(status="recorded")


@router.post("/tokens/ignore", response_model=TokenIgnoreResponse)
def post_token_ignore(payload: TokenIgnoreRequest, request: Request) -> TokenIgnoreResponse:
    engine = getattr(request.app.state, "typo_engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail="Typo engine unavailable.")
    try:
        engine.add_ignored_token(
            payload.token,
            scope=payload.scope,
            expires_at=payload.expires_at,
        )
    except sqlite3.OperationalError as exc:
        logger.exception("token_ignore_db_operational_error")
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}") from exc
    return TokenIgnoreResponse(status="ignored")

from __future__ import annotations

import logging
import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token

router = APIRouter()
logger = logging.getLogger(__name__)


class AddWordRequest(BaseModel):
    surface_token: str = Field(..., min_length=1)
    lemma_candidate: str | None = None


class AddWordResponse(BaseModel):
    status: Literal["inserted", "exists"]
    stored_lemma: str
    stored_surface_form: str | None
    source: Literal["manual"]
    message: str


@router.post("/wordbank/lexemes", response_model=AddWordResponse)
def add_word(payload: AddWordRequest, request: Request) -> AddWordResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )

    db_path = request.app.state.settings.db_path

    normalized_surface = normalize_token(payload.surface_token)
    normalized_lemma = normalize_token(payload.lemma_candidate or "")
    stored_lemma = normalized_lemma or normalized_surface

    if not stored_lemma:
        raise HTTPException(status_code=400, detail="surface_token or lemma_candidate is required")

    inserted_lexeme = False
    inserted_surface_form = False

    try:
        with get_connection(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (lemma, source)
                VALUES (?, ?)
                """,
                (stored_lemma, "manual"),
            )
            inserted_lexeme = cursor.rowcount == 1

            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ?",
                (stored_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise HTTPException(status_code=500, detail="Failed to create or load lexeme")

            if normalized_surface:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source)
                    VALUES (?, ?, ?)
                    """,
                    (lexeme_row["id"], normalized_surface, "manual"),
                )
                inserted_surface_form = cursor.rowcount == 1
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    inserted = inserted_lexeme or inserted_surface_form
    status: Literal["inserted", "exists"] = "inserted" if inserted else "exists"
    message = (
        f"Added '{stored_lemma}' to wordbank."
        if inserted
        else f"'{stored_lemma}' is already in the wordbank."
    )

    return AddWordResponse(
        status=status,
        stored_lemma=stored_lemma,
        stored_surface_form=normalized_surface or None,
        source="manual",
        message=message,
    )

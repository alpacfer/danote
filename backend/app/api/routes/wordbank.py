from __future__ import annotations

import logging
import os
import sqlite3
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.migrations import apply_migrations
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


class LemmaSummary(BaseModel):
    lemma: str
    variation_count: int


class LemmaListResponse(BaseModel):
    items: list[LemmaSummary]


class LemmaDetailsResponse(BaseModel):
    lemma: str
    surface_forms: list[str]


class ResetDatabaseResponse(BaseModel):
    status: Literal["reset"]
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


@router.get("/wordbank/lemmas", response_model=LemmaListResponse)
def list_lemmas(request: Request) -> LemmaListResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )

    db_path = request.app.state.settings.db_path

    try:
        with get_connection(db_path) as conn:
            rows = conn.execute(
                """
                SELECT l.lemma, COUNT(sf.id) AS variation_count
                FROM lexemes l
                LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                GROUP BY l.id, l.lemma
                ORDER BY l.lemma COLLATE NOCASE
                """
            ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return LemmaListResponse(
        items=[
            LemmaSummary(lemma=row["lemma"], variation_count=int(row["variation_count"]))
            for row in rows
        ]
    )


@router.get("/wordbank/lemmas/{lemma}", response_model=LemmaDetailsResponse)
def get_lemma_details(lemma: str, request: Request) -> LemmaDetailsResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )

    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        raise HTTPException(status_code=400, detail="lemma is required")

    db_path = request.app.state.settings.db_path

    try:
        with get_connection(db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, lemma
                FROM lexemes
                WHERE lemma = ?
                """,
                (normalized_lemma,),
            ).fetchone()

            if lexeme_row is None:
                raise HTTPException(status_code=404, detail=f"Lemma '{normalized_lemma}' was not found")

            form_rows = conn.execute(
                """
                SELECT form
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE
                """,
                (lexeme_row["id"],),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database unavailable: {exc}",
        ) from exc

    return LemmaDetailsResponse(
        lemma=lexeme_row["lemma"],
        surface_forms=[row["form"] for row in form_rows],
    )


@router.delete("/wordbank/database", response_model=ResetDatabaseResponse)
def reset_database(request: Request) -> ResetDatabaseResponse:
    if not bool(getattr(request.app.state, "db_ready", False)):
        raise HTTPException(
            status_code=503,
            detail="Database unavailable. Check backend logs and DB path configuration.",
        )

    db_path = request.app.state.settings.db_path

    try:
        if db_path.exists():
            os.remove(db_path)
        apply_migrations(db_path)
        request.app.state.db_ready = True
        request.app.state.db_error = None
    except OSError as exc:
        logger.exception("wordbank_db_reset_os_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database reset failed: {exc}",
        ) from exc
    except sqlite3.OperationalError as exc:
        logger.exception("wordbank_db_reset_operational_error")
        raise HTTPException(
            status_code=503,
            detail=f"Database reset failed: {exc}",
        ) from exc

    return ResetDatabaseResponse(
        status="reset",
        message="Database reset complete.",
    )

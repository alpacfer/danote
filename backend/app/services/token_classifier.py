from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.db.migrations import get_connection
from app.nlp.adapter import NLPAdapter


Classification = Literal["known", "variation", "new"]
MatchSource = Literal["exact", "lemma", "none"]


@dataclass(frozen=True)
class TokenClassification:
    surface_token: str
    normalized_token: str
    lemma_candidate: str | None
    classification: Classification
    match_source: MatchSource
    matched_lemma: str | None = None
    matched_surface_form: str | None = None


class _NullNLPAdapter:
    def tokenize(self, text: str):
        return []

    def lemma_for_token(self, token: str) -> str | None:
        return None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "null"}


def normalize_token(token: str) -> str:
    # Collapse internal whitespace and normalize case for stable exact lookup.
    return " ".join(token.strip().split()).lower()


class LemmaAwareClassifier:
    def __init__(self, db_path: Path, nlp_adapter: NLPAdapter | None = None):
        self.db_path = db_path
        self.nlp_adapter = nlp_adapter or _NullNLPAdapter()

    def classify(self, token: str) -> TokenClassification:
        normalized = normalize_token(token)

        if not normalized:
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=None,
                classification="new",
                match_source="none",
            )

        with get_connection(self.db_path) as conn:
            exact_row = conn.execute(
                """
                SELECT l.lemma, sf.form
                FROM surface_forms sf
                JOIN lexemes l ON l.id = sf.lexeme_id
                WHERE sf.form = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()

            if exact_row is not None:
                return TokenClassification(
                    surface_token=token,
                    normalized_token=normalized,
                    lemma_candidate=exact_row["lemma"],
                    classification="known",
                    match_source="exact",
                    matched_lemma=exact_row["lemma"],
                    matched_surface_form=exact_row["form"],
                )

            # Also treat exact lexeme lemma matches as known when no explicit surface form exists.
            lemma_exact_row = conn.execute(
                """
                SELECT lemma
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            if lemma_exact_row is not None:
                return TokenClassification(
                    surface_token=token,
                    normalized_token=normalized,
                    lemma_candidate=lemma_exact_row["lemma"],
                    classification="known",
                    match_source="exact",
                    matched_lemma=lemma_exact_row["lemma"],
                    matched_surface_form=normalized,
                )

            lemma_candidate = normalize_token(self.nlp_adapter.lemma_for_token(normalized) or "")
            if not lemma_candidate:
                return TokenClassification(
                    surface_token=token,
                    normalized_token=normalized,
                    lemma_candidate=None,
                    classification="new",
                    match_source="none",
                )

            lemma_row = conn.execute(
                """
                SELECT lemma
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (lemma_candidate,),
            ).fetchone()

        if lemma_row is None:
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=lemma_candidate,
                classification="new",
                match_source="none",
            )

        return TokenClassification(
            surface_token=token,
            normalized_token=normalized,
            lemma_candidate=lemma_candidate,
            classification="variation",
            match_source="lemma",
            matched_lemma=lemma_row["lemma"],
            matched_surface_form=None,
        )


# Backward-compatible alias for prior checkpoints.
ExactLookupClassifier = LemmaAwareClassifier

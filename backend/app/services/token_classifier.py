from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.db.migrations import get_connection
from app.nlp.adapter import NLPAdapter
from app.nlp.lemma_candidate_ranker import (
    normalize_candidate,
    pick_best_candidate_in_lexicon,
)
from app.services.typo.typo_engine import TypoEngine, TypoSuggestion


Classification = Literal["known", "variation", "typo_likely", "uncertain", "new"]
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
    suggestions: tuple[TypoSuggestion, ...] = ()
    confidence: float = 0.0
    reason_tags: tuple[str, ...] = ()


class _NullNLPAdapter:
    def tokenize(self, text: str):
        return []

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return []

    def lemma_for_token(self, token: str) -> str | None:
        return None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "null"}


def normalize_token(token: str) -> str:
    # Collapse internal whitespace and normalize case for stable exact lookup.
    return " ".join(token.strip().split()).lower()


class LemmaAwareClassifier:
    def __init__(
        self,
        db_path: Path,
        nlp_adapter: NLPAdapter | None = None,
        typo_engine: TypoEngine | None = None,
    ):
        self.db_path = db_path
        self.nlp_adapter = nlp_adapter or _NullNLPAdapter()
        self.typo_engine = typo_engine

    def classify(self, token: str) -> TokenClassification:
        with get_connection(self.db_path) as conn:
            return self._classify_with_connection(token, conn)

    def classify_many(self, tokens: list[str]) -> list[TokenClassification]:
        if not tokens:
            return []
        with get_connection(self.db_path) as conn:
            normalized_tokens = [normalize_token(token) for token in tokens]
            non_empty_normalized = [token for token in normalized_tokens if token]
            exact_surface_matches, exact_lemma_matches = self._prefetch_exact_matches(conn, non_empty_normalized)
            lemma_candidates_by_token = {
                token: self._lemma_candidates_for_token(token)
                for token in sorted(set(non_empty_normalized))
            }
            lexeme_candidates = sorted(
                {
                    candidate
                    for candidates in lemma_candidates_by_token.values()
                    for candidate in candidates
                }
            )
            prefetched_lemma_candidates = self._prefetch_lemma_candidates(conn, lexeme_candidates)

            results: list[TokenClassification] = []
            for index, token in enumerate(tokens):
                sentence_start = index == 0
                results.append(
                    self._classify_with_connection(
                        token,
                        conn,
                        sentence_start=sentence_start,
                        exact_surface_matches=exact_surface_matches,
                        exact_lemma_matches=exact_lemma_matches,
                        lemma_candidates_by_token=lemma_candidates_by_token,
                        prefetched_lemma_candidates=prefetched_lemma_candidates,
                    )
                )
            return results

    def _prefetch_exact_matches(
        self,
        conn,
        normalized_tokens: list[str],
    ) -> tuple[dict[str, tuple[str, str]], set[str]]:
        if not normalized_tokens:
            return {}, set()

        unique_tokens = sorted(set(normalized_tokens))
        placeholders = ", ".join("?" for _ in unique_tokens)

        surface_rows = conn.execute(
            f"""
            SELECT sf.form, l.lemma
            FROM surface_forms sf
            JOIN lexemes l ON l.id = sf.lexeme_id
            WHERE sf.form IN ({placeholders})
            """,
            tuple(unique_tokens),
        ).fetchall()
        exact_surface_matches = {
            row["form"]: (row["lemma"], row["form"])
            for row in surface_rows
        }

        lemma_rows = conn.execute(
            f"""
            SELECT lemma
            FROM lexemes
            WHERE lemma IN ({placeholders})
            """,
            tuple(unique_tokens),
        ).fetchall()
        exact_lemma_matches = {row["lemma"] for row in lemma_rows}
        return exact_surface_matches, exact_lemma_matches

    def _prefetch_lemma_candidates(
        self,
        conn,
        lemma_candidates: list[str],
    ) -> set[str]:
        if not lemma_candidates:
            return set()

        placeholders = ", ".join("?" for _ in lemma_candidates)
        lemma_rows = conn.execute(
            f"""
            SELECT lemma
            FROM lexemes
            WHERE lemma IN ({placeholders})
            """,
            tuple(lemma_candidates),
        ).fetchall()
        return {normalize_candidate(row["lemma"]) for row in lemma_rows}

    def _classify_with_connection(
        self,
        token: str,
        conn,
        sentence_start: bool = False,
        exact_surface_matches: dict[str, tuple[str, str]] | None = None,
        exact_lemma_matches: set[str] | None = None,
        lemma_candidates_by_token: dict[str, list[str]] | None = None,
        prefetched_lemma_candidates: set[str] | None = None,
    ) -> TokenClassification:
        normalized = normalize_token(token)

        if not normalized:
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=None,
                classification="new",
                match_source="none",
            )

        exact_match = exact_surface_matches.get(normalized) if exact_surface_matches is not None else None
        if exact_match is None:
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
                exact_match = (exact_row["lemma"], exact_row["form"])

        if exact_match is not None:
            matched_lemma, matched_surface_form = exact_match
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=matched_lemma,
                classification="known",
                match_source="exact",
                matched_lemma=matched_lemma,
                matched_surface_form=matched_surface_form,
                reason_tags=("exact_match",),
            )

        lemma_known = normalized in exact_lemma_matches if exact_lemma_matches is not None else None
        if lemma_known is None:
            lemma_exact_row = conn.execute(
                """
                SELECT lemma
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            lemma_known = lemma_exact_row is not None

        # Also treat exact lexeme lemma matches as known when no explicit surface form exists.
        if lemma_known:
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=normalized,
                classification="known",
                match_source="exact",
                matched_lemma=normalized,
                matched_surface_form=normalized,
                reason_tags=("exact_match",),
            )

        lemma_candidates = (
            lemma_candidates_by_token.get(normalized, [])
            if lemma_candidates_by_token is not None
            else self._lemma_candidates_for_token(normalized)
        )
        if not lemma_candidates:
            return self._new_with_typo_fallback(
                token=token,
                normalized=normalized,
                sentence_start=sentence_start,
            )

        lexeme_set = (
            {
                normalize_candidate(candidate)
                for candidate in lemma_candidates
                if normalize_candidate(candidate) in prefetched_lemma_candidates
            }
            if prefetched_lemma_candidates is not None
            else {
                normalize_candidate(row["lemma"])
                for row in conn.execute(
                    f"""
                    SELECT lemma
                    FROM lexemes
                    WHERE lemma IN ({", ".join("?" for _ in lemma_candidates)})
                    """,
                    tuple(lemma_candidates),
                ).fetchall()
            }
        )
        matched_lemma = pick_best_candidate_in_lexicon(
            surface=normalized,
            tag=None,
            primary_tag_candidates=lemma_candidates,
            fallback_candidates=[],
            lexeme_set=lexeme_set,
        )
        lemma_candidate = lemma_candidates[0]

        if matched_lemma is None:
            result = self._new_with_typo_fallback(
                token=token,
                normalized=normalized,
                sentence_start=sentence_start,
            )
            if result.lemma_candidate is None:
                return TokenClassification(
                    surface_token=result.surface_token,
                    normalized_token=result.normalized_token,
                    lemma_candidate=lemma_candidate,
                    classification=result.classification,
                    match_source=result.match_source,
                    matched_lemma=result.matched_lemma,
                    matched_surface_form=result.matched_surface_form,
                    suggestions=result.suggestions,
                    confidence=result.confidence,
                    reason_tags=result.reason_tags,
                )
            return result

        return TokenClassification(
            surface_token=token,
            normalized_token=normalized,
            lemma_candidate=lemma_candidate,
            classification="variation",
            match_source="lemma",
            matched_lemma=matched_lemma,
            matched_surface_form=None,
            reason_tags=("lemma_match",),
        )

    def _new_with_typo_fallback(
        self,
        *,
        token: str,
        normalized: str,
        sentence_start: bool = False,
    ) -> TokenClassification:
        if self.typo_engine is None:
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=None,
                classification="new",
                match_source="none",
            )
        typo_result = self.typo_engine.classify_unknown(
            token=token,
            sentence_start=sentence_start,
        )
        return TokenClassification(
            surface_token=token,
            normalized_token=typo_result.normalized or normalized,
            lemma_candidate=typo_result.suggestions[0].value if typo_result.suggestions else None,
            classification=typo_result.status,
            match_source="none",
            matched_lemma=None,
            matched_surface_form=None,
            suggestions=typo_result.suggestions,
            confidence=typo_result.confidence,
            reason_tags=typo_result.reason_tags,
        )

    def _lemma_candidates_for_token(self, normalized_token: str) -> list[str]:
        raw_candidates = self.nlp_adapter.lemma_candidates_for_token(normalized_token)
        candidates: list[str] = []
        seen: set[str] = set()
        for raw_candidate in raw_candidates:
            candidate = normalize_token(raw_candidate)
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            candidates.append(candidate)

        if candidates:
            return candidates

        fallback = normalize_token(self.nlp_adapter.lemma_for_token(normalized_token) or "")
        if not fallback:
            return []
        return [fallback]


# Backward-compatible alias for prior checkpoints.
ExactLookupClassifier = LemmaAwareClassifier

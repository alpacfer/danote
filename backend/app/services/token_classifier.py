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

Classification = Literal["known", "variation", "typo_likely", "uncertain", "new"]
MatchSource = Literal["exact", "lemma", "none"]
_SQLITE_IN_CLAUSE_BATCH_SIZE = 400


@dataclass(frozen=True)
class TokenClassification:
    surface_token: str
    normalized_token: str
    lemma_candidate: str | None
    classification: Classification
    match_source: MatchSource
    matched_lemma: str | None = None
    matched_surface_form: str | None = None
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
        owner_user_id: int = 1,
    ):
        self.db_path = db_path
        self.nlp_adapter = nlp_adapter or _NullNLPAdapter()
        self.owner_user_id = owner_user_id

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
    ) -> tuple[dict[str, list[tuple[str, str]]], set[str]]:
        if not normalized_tokens:
            return {}, set()

        unique_tokens = sorted(set(normalized_tokens))
        exact_surface_matches: dict[str, list[tuple[str, str]]] = {}
        exact_lemma_matches: set[str] = set()
        owner_user_id = int(self.owner_user_id)

        for token_batch in _chunked(unique_tokens, _SQLITE_IN_CLAUSE_BATCH_SIZE):
            placeholders = ", ".join("?" for _ in token_batch)
            surface_rows = conn.execute(
                f"""
                SELECT sf.form, l.lemma
                FROM surface_forms sf
                JOIN lexemes l ON l.id = sf.lexeme_id
                WHERE l.owner_user_id = {owner_user_id}
                  AND sf.form IN ({placeholders})
                ORDER BY sf.form ASC,
                         sf.seen_count DESC,
                         sf.last_seen_at DESC,
                         sf.id DESC
                """,
                tuple(token_batch),
            ).fetchall()
            for row in surface_rows:
                exact_surface_matches.setdefault(row["form"], []).append((row["lemma"], row["form"]))

            lemma_rows = conn.execute(
                f"""
                SELECT lemma
                FROM lexemes
                WHERE lemma IN ({placeholders})
                  AND owner_user_id = {owner_user_id}
                """,
                tuple(token_batch),
            ).fetchall()
            exact_lemma_matches.update(row["lemma"] for row in lemma_rows)
        return exact_surface_matches, exact_lemma_matches

    def _prefetch_lemma_candidates(
        self,
        conn,
        lemma_candidates: list[str],
    ) -> set[str]:
        if not lemma_candidates:
            return set()

        prefetched: set[str] = set()
        owner_user_id = int(self.owner_user_id)
        for candidate_batch in _chunked(lemma_candidates, _SQLITE_IN_CLAUSE_BATCH_SIZE):
            placeholders = ", ".join("?" for _ in candidate_batch)
            lemma_rows = conn.execute(
                f"""
                SELECT lemma
                FROM lexemes
                WHERE lemma IN ({placeholders})
                  AND owner_user_id = {owner_user_id}
                """,
                tuple(candidate_batch),
            ).fetchall()
            prefetched.update(normalize_candidate(row["lemma"]) for row in lemma_rows)
        return prefetched

    def _classify_with_connection(
        self,
        token: str,
        conn,
        sentence_start: bool = False,
        exact_surface_matches: dict[str, list[tuple[str, str]]] | None = None,
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

        exact_matches = exact_surface_matches.get(normalized) if exact_surface_matches is not None else None
        if exact_matches is None:
            owner_user_id = int(self.owner_user_id)
            exact_rows = conn.execute(
                f"""
                SELECT l.lemma, sf.form
                FROM surface_forms sf
                JOIN lexemes l ON l.id = sf.lexeme_id
                WHERE l.owner_user_id = {owner_user_id}
                  AND sf.form = ?
                ORDER BY sf.seen_count DESC,
                         sf.last_seen_at DESC,
                         sf.id DESC
                """,
                (normalized,),
            ).fetchall()
            exact_matches = [(row["lemma"], row["form"]) for row in exact_rows]

        if exact_matches:
            lemma_candidates = (
                lemma_candidates_by_token.get(normalized, [])
                if lemma_candidates_by_token is not None
                else self._lemma_candidates_for_token(normalized)
            )
            exact_match = self._pick_best_exact_match(normalized, exact_matches, lemma_candidates)
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
            owner_user_id = int(self.owner_user_id)
            lemma_exact_row = conn.execute(
                f"""
                SELECT lemma
                FROM lexemes
                WHERE owner_user_id = {owner_user_id}
                  AND lemma = ?
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
            return TokenClassification(
                surface_token=token,
                normalized_token=normalized,
                lemma_candidate=None,
                classification="new",
                match_source="none",
            )

        if prefetched_lemma_candidates is not None:
            lexeme_set: set[str] = set()
            for candidate in lemma_candidates:
                normalized_candidate = normalize_candidate(candidate)
                if normalized_candidate in prefetched_lemma_candidates:
                    lexeme_set.add(normalized_candidate)
        else:
            owner_user_id = int(self.owner_user_id)
            lexeme_set = {
                normalize_candidate(row["lemma"])
                for row in conn.execute(
                    f"""
                    SELECT lemma
                    FROM lexemes
                    WHERE lemma IN ({", ".join("?" for _ in lemma_candidates)})
                      AND owner_user_id = {owner_user_id}
                    """,
                    tuple(lemma_candidates),
                ).fetchall()
            }
        matched_lemma = pick_best_candidate_in_lexicon(
            surface=normalized,
            tag=None,
            primary_tag_candidates=lemma_candidates,
            fallback_candidates=[],
            lexeme_set=lexeme_set,
        )
        lemma_candidate = lemma_candidates[0]

        if matched_lemma is None:
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
            matched_lemma=matched_lemma,
            matched_surface_form=None,
            reason_tags=("lemma_match",),
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

    def _pick_best_exact_match(
        self,
        surface: str,
        exact_matches: list[tuple[str, str]],
        lemma_candidates: list[str],
    ) -> tuple[str, str]:
        if len(exact_matches) == 1 or not lemma_candidates:
            return exact_matches[0]

        exact_lemmas = {normalize_candidate(match[0]) for match in exact_matches}
        matched_lemma = pick_best_candidate_in_lexicon(
            surface=surface,
            tag=None,
            primary_tag_candidates=lemma_candidates,
            fallback_candidates=[],
            lexeme_set=exact_lemmas,
        )
        if matched_lemma is None:
            return exact_matches[0]

        for lemma, form in exact_matches:
            if normalize_candidate(lemma) == matched_lemma:
                return (lemma, form)
        return exact_matches[0]


# Backward-compatible alias for prior checkpoints.
ExactLookupClassifier = LemmaAwareClassifier


def _chunked(values: list[str], size: int) -> list[list[str]]:
    if size <= 0:
        raise ValueError("Chunk size must be greater than zero")
    return [values[index : index + size] for index in range(0, len(values), size)]

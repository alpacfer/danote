from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.db.migrations import get_connection
from app.services.typo.cache import LRUCache
from app.services.typo.candidates import CandidateProvider
from app.services.typo.decision import decide_status
from app.services.typo.gating import should_run_typo_check
from app.services.typo.normalization import ComparisonForms, comparison_forms
from app.services.typo.ranking import rank_candidates


TypoStatus = Literal["typo_likely", "uncertain", "new"]


@dataclass(frozen=True)
class TypoSuggestion:
    value: str
    score: float
    source_flags: tuple[str, ...]


@dataclass(frozen=True)
class TypoResult:
    status: TypoStatus
    normalized: str
    suggestions: tuple[TypoSuggestion, ...]
    confidence: float
    reason_tags: tuple[str, ...]
    latency_ms: float




@dataclass(frozen=True)
class DecisionThresholds:
    typo_threshold: float
    uncertain_threshold: float
    min_margin: float


def _load_decision_thresholds() -> DecisionThresholds:
    policy_path = Path(__file__).resolve().parents[2] / "core" / "typo_policy.v1.json"
    default = DecisionThresholds(typo_threshold=0.78, uncertain_threshold=0.5, min_margin=0.08)
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
        node = payload.get("decision_thresholds", {})
        return DecisionThresholds(
            typo_threshold=float(node.get("typo_likely_min_confidence", default.typo_threshold)),
            uncertain_threshold=float(node.get("uncertain_min_confidence", default.uncertain_threshold)),
            min_margin=float(node.get("min_top1_top2_margin", default.min_margin)),
        )
    except Exception:
        return default


class TypoEngine:
    def __init__(
        self,
        *,
        db_path: Path,
        dictionary_path: Path | None = None,
        dictionary_paths: tuple[Path, ...] | None = None,
    ):
        self.db_path = db_path
        self.candidates = CandidateProvider(
            db_path=db_path,
            dictionary_path=dictionary_path,
            dictionary_paths=dictionary_paths,
        )
        self.cache = LRUCache[str, TypoResult](max_size=4096)
        self._ignored_tokens_cache: set[str] | None = None
        self._decision_thresholds = _load_decision_thresholds()

    def classify_unknown(
        self,
        *,
        token: str,
        sentence_start: bool = False,
    ) -> TypoResult:
        started = time.perf_counter()
        forms = comparison_forms(token)
        gating = should_run_typo_check(
            token=token,
            normalized=forms.normalized,
            sentence_start=sentence_start,
        )
        if not gating.should_run:
            result = TypoResult(
                status="new",
                normalized=forms.normalized,
                suggestions=(),
                confidence=0.0,
                reason_tags=gating.reason_tags,
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            self._log_event(token=token, result=result)
            return result

        if self._is_ignored(forms.normalized):
            result = TypoResult(
                status="new",
                normalized=forms.normalized,
                suggestions=(),
                confidence=0.0,
                reason_tags=("gating_skip_ignored",),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            self._log_event(token=token, result=result)
            return result

        cache_key = f"{forms.normalized}|{int(sentence_start)}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            return cached

        if any(self.candidates.is_known_dictionary_word(form) for form in forms.alternates):
            result = TypoResult(
                status="new",
                normalized=forms.normalized,
                suggestions=(),
                confidence=0.0,
                reason_tags=gating.reason_tags + ("gating_skip_dictionary_exact",),
                latency_ms=(time.perf_counter() - started) * 1000.0,
            )
            self.cache.set(cache_key, result)
            self._log_event(token=token, result=result)
            return result

        max_distance = _max_distance_for_length(
            len(forms.normalized),
            large_dictionary=self.candidates.general_word_count >= 500_000,
        )
        candidates = self.candidates.suggest(
            forms.normalized,
            max_candidates=20,
            max_distance=max_distance,
        )
        known_lemmas = self._known_lemmas()
        ranked = rank_candidates(token=forms.normalized, candidates=candidates, known_lemmas=known_lemmas)
        decision = decide_status(
            ranked=ranked,
            proper_noun_bias=gating.proper_noun_bias,
            typo_threshold=self._decision_thresholds.typo_threshold,
            uncertain_threshold=self._decision_thresholds.uncertain_threshold,
            min_margin=self._decision_thresholds.min_margin,
        )

        resolved_status, resolution_tags = self._resolve_status_by_dictionary_membership(
            status=decision.status,
            forms=forms,
        )
        suggestions = tuple(
            TypoSuggestion(value=item.value, score=item.score, source_flags=item.source_flags)
            for item in ranked[:3]
        )
        result = TypoResult(
            status=resolved_status,
            normalized=forms.normalized,
            suggestions=suggestions,
            confidence=decision.confidence,
            reason_tags=gating.reason_tags + decision.reason_tags + resolution_tags,
            latency_ms=(time.perf_counter() - started) * 1000.0,
        )
        self.cache.set(cache_key, result)
        self._log_event(token=token, result=result)
        return result

    def add_user_lexeme(self, lemma: str) -> None:
        self.candidates.add_user_lexeme(lemma)
        self.cache.clear()

    def invalidate_cache(self) -> None:
        self.cache.clear()

    def add_ignored_token(self, token: str, *, scope: str = "global", expires_at: str | None = None) -> None:
        normalized = comparison_forms(token).normalized
        if not normalized:
            return
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO ignored_tokens (token, scope, expires_at)
                VALUES (?, ?, ?)
                ON CONFLICT(token, scope)
                DO UPDATE SET expires_at = excluded.expires_at
                """,
                (normalized, scope, expires_at),
            )
        if self._ignored_tokens_cache is not None:
            self._ignored_tokens_cache.add(normalized)
        self.cache.clear()

    def add_feedback(
        self,
        *,
        raw_token: str,
        predicted_status: str,
        suggestions_shown: list[str],
        user_action: str,
        chosen_value: str | None = None,
    ) -> None:
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO typo_feedback
                (raw_token, predicted_status, suggestions_shown, user_action, chosen_value)
                VALUES (?, ?, ?, ?, ?)
                """,
                (raw_token, predicted_status, json.dumps(suggestions_shown), user_action, chosen_value),
            )

    def _is_ignored(self, normalized: str) -> bool:
        if self._ignored_tokens_cache is None:
            self._ignored_tokens_cache = self._ignored_tokens_from_db()
        return normalized in self._ignored_tokens_cache

    def _ignored_tokens_from_db(self) -> set[str]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute(
                """
                SELECT token
                FROM ignored_tokens
                WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                """
            ).fetchall()
        return {str(row["token"]) for row in rows}

    def _known_lemmas(self) -> set[str]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT lemma FROM lexemes").fetchall()
        return {str(row["lemma"]) for row in rows}

    def _log_event(self, *, token: str, result: TypoResult) -> None:
        top = result.suggestions[0].value if result.suggestions else None
        with get_connection(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO token_events
                (raw_token, normalized_token, final_status, top_suggestion, confidence, latency_ms)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    token,
                    result.normalized,
                    result.status,
                    top,
                    result.confidence,
                    result.latency_ms,
                ),
            )

    def _resolve_status_by_dictionary_membership(
        self,
        *,
        status: TypoStatus,
        forms: ComparisonForms,
    ) -> tuple[TypoStatus, tuple[str, ...]]:
        in_dictionary = any(self.candidates.is_known_dictionary_word(form) for form in forms.alternates)
        if in_dictionary:
            if status == "uncertain":
                return "new", ("uncertain_resolved_dictionary_hit",)
            return status, ()
        if status in {"new", "uncertain"}:
            return "typo_likely", ("dictionary_miss_forced_typo",)
        return status, ()


def _max_distance_for_length(length: int, *, large_dictionary: bool = False) -> int:
    if large_dictionary:
        # Large lexicons dramatically increase candidate search cost at edit distance 2.
        # Keep typo checks responsive by restricting to distance 1 in this mode.
        return 1
    if length <= 4:
        return 1
    if length <= 8:
        return 2
    return 2

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from app.db.migrations import get_connection
from app.services.typo.normalization import comparison_forms

try:
    from symspellpy.symspellpy import SymSpell, Verbosity
except Exception:  # pragma: no cover - optional dependency
    SymSpell = None
    Verbosity = None


@dataclass(frozen=True)
class Candidate:
    value: str
    distance: int
    source_flags: tuple[str, ...]
    frequency: float


class CandidateProvider:
    def __init__(
        self,
        *,
        db_path: Path,
        dictionary_path: Path | None = None,
        dictionary_paths: Iterable[Path] | None = None,
        max_dictionary_edit_distance: int = 2,
        prefix_length: int = 7,
    ) -> None:
        self.db_path = db_path
        self.dictionary_paths = self._resolve_dictionary_paths(
            dictionary_path=dictionary_path,
            dictionary_paths=dictionary_paths,
        )
        self.max_dictionary_edit_distance = max_dictionary_edit_distance
        self.prefix_length = prefix_length
        self._symspell = None
        self._general_words: set[str] = set()
        self._suggestion_words: set[str] = set()
        self.general_word_count = 0
        self._load()

    def _resolve_dictionary_paths(
        self,
        *,
        dictionary_path: Path | None,
        dictionary_paths: Iterable[Path] | None,
    ) -> tuple[Path, ...]:
        resolved: list[Path] = []
        if dictionary_path is not None:
            resolved.append(dictionary_path)
        if dictionary_paths is not None:
            resolved.extend(dictionary_paths)
        seen: set[Path] = set()
        unique_paths: list[Path] = []
        for path in resolved:
            if path in seen:
                continue
            seen.add(path)
            unique_paths.append(path)
        return tuple(unique_paths)

    def _load(self) -> None:
        self._general_words = set()
        self._suggestion_words = set()
        for dictionary_path in self.dictionary_paths:
            if not dictionary_path.exists():
                continue
            words = {
                line.strip().lower()
                for line in dictionary_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            }
            self._general_words.update(words)
            if not _is_membership_only_dictionary(dictionary_path):
                self._suggestion_words.update(words)
        self.general_word_count = len(self._general_words)
        if SymSpell is not None:
            self._symspell = SymSpell(
                max_dictionary_edit_distance=self.max_dictionary_edit_distance,
                prefix_length=self.prefix_length,
            )
            for word in self._suggestion_words:
                self._symspell.create_dictionary_entry(word, 10)
            for lemma in self._load_user_lemmas():
                self._symspell.create_dictionary_entry(lemma, 100)

    def _load_user_lemmas(self) -> set[str]:
        with get_connection(self.db_path) as conn:
            rows = conn.execute("SELECT lemma FROM lexemes").fetchall()
        return {str(row["lemma"]).lower() for row in rows}

    def add_user_lexeme(self, lemma: str) -> None:
        normalized = lemma.strip().lower()
        if not normalized:
            return
        if self._symspell is not None:
            self._symspell.create_dictionary_entry(normalized, 100)

    def refresh_user_lexicon(self) -> None:
        if self._symspell is None:
            return
        self._load()

    def is_valid_word(self, token: str) -> bool:
        normalized = token.strip().lower()
        if not normalized:
            return False
        if self.is_known_dictionary_word(normalized):
            return True
        with get_connection(self.db_path) as conn:
            row = conn.execute(
                "SELECT 1 FROM lexemes WHERE lemma = ? LIMIT 1",
                (normalized,),
            ).fetchone()
        return row is not None

    def is_known_dictionary_word(self, token: str) -> bool:
        normalized = token.strip().lower()
        if not normalized:
            return False
        return normalized in self._general_words

    def suggest(self, token: str, *, max_candidates: int = 10, max_distance: int = 2) -> list[Candidate]:
        forms = comparison_forms(token)
        all_candidates: dict[str, Candidate] = {}
        for form in forms.alternates:
            for candidate in self._suggest_one(form, max_candidates=max_candidates, max_distance=max_distance):
                previous = all_candidates.get(candidate.value)
                if previous is None or candidate.distance < previous.distance:
                    all_candidates[candidate.value] = candidate
        ranked = sorted(
            all_candidates.values(),
            key=lambda item: (item.distance, -item.frequency, item.value),
        )
        return ranked[:max_candidates]

    def _suggest_one(self, normalized: str, *, max_candidates: int, max_distance: int) -> Iterable[Candidate]:
        if not normalized:
            return []

        if self._symspell is not None and Verbosity is not None:
            results = self._symspell.lookup(
                normalized,
                Verbosity.CLOSEST,
                max_edit_distance=min(max_distance, self.max_dictionary_edit_distance),
                include_unknown=False,
                transfer_casing=False,
            )
            return [
                Candidate(
                    value=result.term,
                    distance=int(result.distance),
                    source_flags=("from_symspell",),
                    frequency=float(result.count),
                )
                for result in results[:max_candidates]
            ]

        # Fallback path without SymSpell dependency.
        user_lemmas = self._load_user_lemmas()
        words = self._suggestion_words | user_lemmas
        scored = []
        for word in words:
            distance = _levenshtein(normalized, word)
            if distance <= max_distance:
                source = "from_user_dict" if word in user_lemmas else "from_general_dict"
                score = 100.0 if source == "from_user_dict" else 10.0
                scored.append(Candidate(value=word, distance=distance, source_flags=(source,), frequency=score))
        return sorted(scored, key=lambda item: (item.distance, -item.frequency, item.value))[:max_candidates]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (0 if ca == cb else 1)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]


def _is_membership_only_dictionary(path: Path) -> bool:
    try:
        size_bytes = path.stat().st_size
    except OSError:
        return False
    # Very large dictionaries are useful for exact validity checks,
    # but too expensive for broad typo-candidate search.
    return size_bytes >= 5_000_000

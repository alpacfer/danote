# Typo-tolerant Search Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the unused complex TypoEngine with a simple Levenshtein-based fuzzy fallback in search: when no results found, return corrected results + `did_you_mean` string; show "Did you mean X?" as a selectable item that replaces the query in-place.

**Architecture:** New pure `fuzzy_search.py` module with `levenshtein()` + `fuzzy_suggest()`. Backend `search_lemmas` and `search_cor_form` use it as fallback when result set is empty. Frontend `useSidebarSearch` exposes `didYouMean`, and `SidebarSearchResults` renders a keyboard-navigable `CommandItem` for it.

**Tech Stack:** Python (pure stdlib), FastAPI/Pydantic, React 19, TypeScript, shadcn/ui `CommandItem`

---

## File map

| Action | Path |
|--------|------|
| **Create** | `backend/app/services/fuzzy_search.py` |
| **Create** | `backend/tests/services/test_fuzzy_search.py` |
| **Create** | `backend/tests/use_cases/test_wordbank_search_typo.py` |
| **Modify** | `backend/app/services/token_classifier.py` |
| **Modify** | `backend/app/services/use_cases/analyze.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/collaborators/nlp.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/collaborators/cor_resolution.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/core.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/background_jobs.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/queries_lemmas.py` |
| **Modify** | `backend/app/api/routes/analyze.py` |
| **Modify** | `backend/app/api/routes/_use_case_factories.py` |
| **Modify** | `backend/app/api/router.py` |
| **Modify** | `backend/app/api/schemas/v1/wordbank.py` |
| **Modify** | `backend/app/bootstrap/runtime.py` |
| **Modify** | `backend/app/core/app_state.py` |
| **Modify** | `backend/app/core/config.py` |
| **Modify** | `backend/app/db/repositories/wordbank_reads.py` |
| **Modify** | `backend/app/services/cor_local.py` |
| **Modify** | `backend/app/services/use_cases/wordbank/collaborators/cor_local.py` |
| **Modify** | `backend/tests/helpers/fakes.py` |
| **Modify** | `backend/tests/services/test_token_classifier_unit.py` |
| **Modify** | `frontend/src/app/core/types-api.ts` |
| **Modify** | `frontend/src/app/chrome/sidebar/use-sidebar-search.ts` |
| **Modify** | `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx` |
| **Modify** | `frontend/src/app/chrome/sidebar/app-sidebar.tsx` |
| **Modify** | `frontend/src/test/app/mock-fetch.ts` |
| **Modify** | `frontend/src/test/app/app-shell-search-basics.test.tsx` |
| **Modify** | `docs/api-contract.md` |
| **Delete** | `backend/app/services/typo/` (entire folder) |
| **Delete** | `backend/app/bootstrap/runtime_typo.py` |
| **Delete** | `backend/app/api/routes/tokens.py` |
| **Delete** | `backend/tests/services/test_typo_engine_unit.py` |
| **Delete** | `backend/tests/services/test_typo_feature_extensive.py` |
| **Delete** | `backend/tests/services/test_typo_ranking_decision_unit.py` |

---

## Task 1: Create `fuzzy_search.py`

**Files:**
- Create: `backend/app/services/fuzzy_search.py`
- Create: `backend/tests/services/test_fuzzy_search.py`

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/services/test_fuzzy_search.py`:

```python
from __future__ import annotations

import pytest

from app.services.fuzzy_search import levenshtein, fuzzy_suggest


def test_levenshtein_identical():
    assert levenshtein("hus", "hus") == 0


def test_levenshtein_single_insert():
    assert levenshtein("hus", "huse") == 1


def test_levenshtein_single_delete():
    assert levenshtein("huse", "hus") == 1


def test_levenshtein_single_replace():
    assert levenshtein("huse", "huke") == 1


def test_levenshtein_empty_a():
    assert levenshtein("", "hus") == 3


def test_levenshtein_empty_b():
    assert levenshtein("hus", "") == 3


def test_levenshtein_two_edits():
    assert levenshtein("biler", "bilen") == 2


def test_fuzzy_suggest_returns_closest():
    result = fuzzy_suggest("huse", ["hus", "bil", "huse"], max_distance=2)
    assert "hus" in result


def test_fuzzy_suggest_excludes_exact_match():
    result = fuzzy_suggest("huse", ["hus", "huse"])
    assert "huse" not in result


def test_fuzzy_suggest_excludes_by_length_prefilter():
    # diff > max_distance=2, must be filtered before computing Levenshtein
    result = fuzzy_suggest("ab", ["abcdefgh"], max_distance=2)
    assert result == []


def test_fuzzy_suggest_respects_max_results():
    candidates = ["kat", "kar", "kan", "kab", "kas"]
    result = fuzzy_suggest("kaf", candidates, max_distance=1, max_results=3)
    assert len(result) <= 3


def test_fuzzy_suggest_case_insensitive():
    result = fuzzy_suggest("Huse", ["HUS", "Bil"], max_distance=2)
    assert "hus" in result


def test_fuzzy_suggest_no_match_returns_empty():
    result = fuzzy_suggest("xyz", ["abc", "def"], max_distance=1)
    assert result == []


def test_fuzzy_suggest_deduplicates_case_variants():
    # "HUS" and "hus" are same after lowercasing; appear once
    result = fuzzy_suggest("huse", ["HUS", "hus"], max_distance=2)
    assert result.count("hus") == 1
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_fuzzy_search.py
```

Expected: `ModuleNotFoundError: No module named 'app.services.fuzzy_search'`

- [ ] **Step 3: Implement `fuzzy_search.py`**

Create `backend/app/services/fuzzy_search.py`:

```python
from __future__ import annotations

from typing import Iterable


def levenshtein(a: str, b: str) -> int:
    """Wagner-Fischer dynamic programming Levenshtein distance."""
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
            curr.append(min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + (0 if ca == cb else 1)))
        prev = curr
    return prev[-1]


def fuzzy_suggest(
    query: str,
    candidates: Iterable[str],
    *,
    max_distance: int = 2,
    max_results: int = 3,
) -> list[str]:
    """Return up to max_results candidates within Levenshtein distance of query.

    - Comparison is case-insensitive; results are returned lowercased.
    - Exact matches (distance 0) are excluded — callers use this for typo correction only.
    - Pre-filters by length diff to keep scans fast over large vocabularies.
    """
    query_lower = query.lower()
    scored: list[tuple[int, str]] = []
    for candidate in candidates:
        candidate_lower = candidate.lower()
        if abs(len(query_lower) - len(candidate_lower)) > max_distance:
            continue
        dist = levenshtein(query_lower, candidate_lower)
        if 0 < dist <= max_distance:
            scored.append((dist, candidate_lower))
    scored.sort(key=lambda x: (x[0], x[1]))
    seen: set[str] = set()
    result: list[str] = []
    for _, word in scored:
        if word not in seen:
            seen.add(word)
            result.append(word)
        if len(result) >= max_results:
            break
    return result
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_fuzzy_search.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/fuzzy_search.py backend/tests/services/test_fuzzy_search.py
git commit -m "feat: add fuzzy_search module with Levenshtein distance"
```

---

## Task 2: Strip TypoEngine from token_classifier and analyze use case

**Files:**
- Modify: `backend/app/services/token_classifier.py`
- Modify: `backend/app/services/use_cases/analyze.py`
- Modify: `backend/tests/services/test_token_classifier_unit.py`

- [ ] **Step 1: Simplify `token_classifier.py`**

Open `backend/app/services/token_classifier.py`.

**Remove line 13** (the `TypoEngine` / `TypoSuggestion` import):
```python
# DELETE this line:
from app.services.typo.typo_engine import TypoEngine, TypoSuggestion
```

**Remove the `suggestions` field from `TokenClassification`** (line ~30):
```python
# BEFORE:
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

# AFTER:
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
```

**Remove `typo_engine` param from `LemmaAwareClassifier.__init__`** (lines ~54-63):
```python
# BEFORE:
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

# AFTER:
class LemmaAwareClassifier:
    def __init__(
        self,
        db_path: Path,
        nlp_adapter: NLPAdapter | None = None,
    ):
        self.db_path = db_path
        self.nlp_adapter = nlp_adapter or _NullNLPAdapter()
```

**Replace the two `self._new_with_typo_fallback(...)` call sites** with direct "new" returns. Both calls look like:
```python
return self._new_with_typo_fallback(
    token=token,
    normalized=normalized,
    sentence_start=sentence_start,
)
```
Replace each with:
```python
return TokenClassification(
    surface_token=token,
    normalized_token=normalized,
    lemma_candidate=None,
    classification="new",
    match_source="none",
)
```

**Delete the entire `_new_with_typo_fallback` method** (lines ~321-351).

- [ ] **Step 2: Simplify `analyze.py`**

Open `backend/app/services/use_cases/analyze.py`.

Remove `typo_engine` parameter from `AnalyzeNoteUseCase.__init__`:
```python
# BEFORE:
class AnalyzeNoteUseCase:
    def __init__(self, db_path, nlp_adapter: NLPAdapter, typo_engine=None):
        self._db_path = db_path
        self._nlp_adapter = nlp_adapter
        self._typo_engine = typo_engine

    def execute(self, text: str) -> list[AnalyzedToken]:
        ...
        classifier = LemmaAwareClassifier(
            self._db_path,
            nlp_adapter=self._nlp_adapter,
            typo_engine=self._typo_engine,
        )

# AFTER:
class AnalyzeNoteUseCase:
    def __init__(self, db_path, nlp_adapter: NLPAdapter):
        self._db_path = db_path
        self._nlp_adapter = nlp_adapter

    def execute(self, text: str) -> list[AnalyzedToken]:
        ...
        classifier = LemmaAwareClassifier(
            self._db_path,
            nlp_adapter=self._nlp_adapter,
        )
```

Replace the `suggestions` mapping (lines ~60-67) with an empty list — `result.suggestions` no longer exists:
```python
# BEFORE:
suggestions=[
    {
        "value": suggestion.value,
        "score": suggestion.score,
        "source_flags": list(suggestion.source_flags),
    }
    for suggestion in result.suggestions
],

# AFTER:
suggestions=[],
```

- [ ] **Step 3: Update `test_token_classifier_unit.py`**

Open `backend/tests/services/test_token_classifier_unit.py`.

Remove the entire `test_unknown_can_fallback_to_typo_engine` test function (lines ~192-208) and any stub/helper classes used only by that test (`_StubTypoEngine`, etc.). Also remove the `from app.services.typo.typo_engine import TypoResult, TypoSuggestion` import at line 7.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/services/test_token_classifier_unit.py
```

Expected: all remaining tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/token_classifier.py backend/app/services/use_cases/analyze.py backend/tests/services/test_token_classifier_unit.py
git commit -m "refactor: strip TypoEngine from token classifier and analyze use case"
```

---

## Task 3: Strip TypoEngine from wordbank collaborators + use case core

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/collaborators/nlp.py`
- Modify: `backend/app/services/use_cases/wordbank/collaborators/cor_resolution.py`
- Modify: `backend/app/services/use_cases/wordbank/core.py`
- Modify: `backend/app/services/use_cases/wordbank/background_jobs.py`

- [ ] **Step 1: Simplify `collaborators/nlp.py`**

Open `backend/app/services/use_cases/wordbank/collaborators/nlp.py`.

Remove `typo_engine` from `NLPCollaborator.__init__`, remove the `invalidate_typo_cache` and `add_user_lexeme` typo calls, and remove the `typo_engine` property:

```python
# BEFORE:
class NLPCollaborator:
    def __init__(
        self,
        nlp_adapter,
        typo_engine,
        cor_lexicon_service: CORLexiconService | None = None,
    ) -> None:
        self._nlp_adapter = nlp_adapter
        self._typo_engine = typo_engine
        self._cor_lexicon_service = cor_lexicon_service
        self._pos_morph_cache: dict[tuple[str, str | None], tuple[str | None, str | None]] = {}

    def invalidate_typo_cache(self) -> None:
        if self._typo_engine is not None:
            self._typo_engine.invalidate_cache()

    def add_user_lexeme(self, lemma: str) -> None:
        if self._typo_engine is not None:
            self._typo_engine.add_user_lexeme(lemma)

    @property
    def typo_engine(self):
        return self._typo_engine

# AFTER:
class NLPCollaborator:
    def __init__(
        self,
        nlp_adapter,
        cor_lexicon_service: CORLexiconService | None = None,
    ) -> None:
        self._nlp_adapter = nlp_adapter
        self._cor_lexicon_service = cor_lexicon_service
        self._pos_morph_cache: dict[tuple[str, str | None], tuple[str | None, str | None]] = {}

    def invalidate_typo_cache(self) -> None:
        pass  # no-op: typo engine removed

    def add_user_lexeme(self, lemma: str) -> None:
        pass  # no-op: typo engine removed
```

- [ ] **Step 2: Simplify `cor_resolution.py`**

Open `backend/app/services/use_cases/wordbank/collaborators/cor_resolution.py`.

Remove `typo_engine=nlp.typo_engine` from the `LemmaAwareClassifier(...)` call (line ~60):

```python
# BEFORE:
classifier = LemmaAwareClassifier(
    db_path,
    nlp_adapter=None,
    typo_engine=nlp.typo_engine,
)

# AFTER:
classifier = LemmaAwareClassifier(
    db_path,
    nlp_adapter=None,
)
```

- [ ] **Step 3: Remove `typo_engine` from `wordbank/core.py`**

Open `backend/app/services/use_cases/wordbank/core.py`.

Remove `typo_engine=None` from `WordbankUseCase.__init__` signature and remove it from the `NLPCollaborator(...)` call:

```python
# BEFORE (lines ~51-65):
class WordbankUseCase:
    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service=None,
        ...
    ):
        nlp = NLPCollaborator(nlp_adapter, typo_engine, cor_lexicon_service)

# AFTER:
class WordbankUseCase:
    def __init__(
        self,
        db_path,
        translation_service=None,
        ...
    ):
        nlp = NLPCollaborator(nlp_adapter, cor_lexicon_service)
```

- [ ] **Step 4: Remove `typo_engine` from `background_jobs.py`**

Open `backend/app/services/use_cases/wordbank/background_jobs.py`.

Find the `WordbankUseCase(...)` call (~line 157) and remove `typo_engine=self._services.typo_engine`:

```python
# BEFORE:
use_case = WordbankUseCase(
    self._db_path,
    typo_engine=self._services.typo_engine,
    translation_service=self._services.translation_service,
    ...
)

# AFTER:
use_case = WordbankUseCase(
    self._db_path,
    translation_service=self._services.translation_service,
    ...
)
```

- [ ] **Step 5: Run tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/use_cases/wordbank/collaborators/nlp.py \
        backend/app/services/use_cases/wordbank/collaborators/cor_resolution.py \
        backend/app/services/use_cases/wordbank/core.py \
        backend/app/services/use_cases/wordbank/background_jobs.py
git commit -m "refactor: strip TypoEngine from wordbank collaborators and use case"
```

---

## Task 4: Strip TypoEngine from API routes, bootstrap, and app_state/config

**Files:**
- Modify: `backend/app/api/routes/analyze.py`
- Modify: `backend/app/api/routes/_use_case_factories.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/app/bootstrap/runtime.py`
- Modify: `backend/app/core/app_state.py`
- Modify: `backend/app/core/config.py`

- [ ] **Step 1: Update `api/routes/analyze.py`**

Remove `typo_engine=services.typo_engine` from the `AnalyzeNoteUseCase(...)` call:

```python
# BEFORE:
use_case = AnalyzeNoteUseCase(
    settings.db_path,
    nlp_adapter=services.nlp_adapter,
    typo_engine=services.typo_engine,
)

# AFTER:
use_case = AnalyzeNoteUseCase(
    settings.db_path,
    nlp_adapter=services.nlp_adapter,
)
```

- [ ] **Step 2: Update `_use_case_factories.py`**

Open `backend/app/api/routes/_use_case_factories.py`. Remove `typo_engine=services.typo_engine` from `WordbankUseCase(...)`.

- [ ] **Step 3: Update `api/router.py`**

Open `backend/app/api/router.py`. Remove the tokens router:

```python
# DELETE these lines:
from app.api.routes.tokens import router as tokens_router
...
api_router.include_router(tokens_router)
```

- [ ] **Step 4: Update `bootstrap/runtime.py`**

Open `backend/app/bootstrap/runtime.py`.

Remove the `initialize_typo` import (line 17):
```python
# DELETE:
from app.bootstrap.runtime_typo import initialize_typo
```

Remove the startup step (line ~68):
```python
# DELETE from build_startup_steps():
StartupStep("typo", initialize_typo),
```

Remove the `typo_enabled` log line (~line 95):
```python
# DELETE:
"typo_enabled": bool(services.typo_engine is not None),
```

- [ ] **Step 5: Update `core/app_state.py`**

Open `backend/app/core/app_state.py`. Remove `typo_engine: Any = None` from `BackendServices`.

- [ ] **Step 6: Update `core/config.py`**

Open `backend/app/core/config.py`.

Remove `typo_enabled: bool = True` and `typo_dictionary_path: Path | None = None` from `Settings`.

Remove these lines from `load_settings()`:
```python
# DELETE:
typo_dictionary_path = _optional_env("DANOTE_TYPO_DICTIONARY_PATH", env_values)
...
typo_enabled=_required_env("DANOTE_TYPO_ENABLED", env_values, "1").lower() not in {"0", "false", "no"},
typo_dictionary_path=Path(typo_dictionary_path) if typo_dictionary_path else None,
```

- [ ] **Step 7: Run tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all tests pass (some typo-specific tests still exist but will be deleted in Task 5).

- [ ] **Step 8: Commit**

```bash
git add backend/app/api/routes/analyze.py \
        backend/app/api/routes/_use_case_factories.py \
        backend/app/api/router.py \
        backend/app/bootstrap/runtime.py \
        backend/app/core/app_state.py \
        backend/app/core/config.py
git commit -m "refactor: remove TypoEngine wiring from routes, bootstrap, and config"
```

---

## Task 5: Delete old typo engine code

**Files to delete:**
- `backend/app/services/typo/` (entire folder)
- `backend/app/bootstrap/runtime_typo.py`
- `backend/app/api/routes/tokens.py`
- `backend/tests/services/test_typo_engine_unit.py`
- `backend/tests/services/test_typo_feature_extensive.py`
- `backend/tests/services/test_typo_ranking_decision_unit.py`

- [ ] **Step 1: Delete files**

```bash
rm -rf backend/app/services/typo/
rm backend/app/bootstrap/runtime_typo.py
rm backend/app/api/routes/tokens.py
rm backend/tests/services/test_typo_engine_unit.py
rm backend/tests/services/test_typo_feature_extensive.py
rm backend/tests/services/test_typo_ranking_decision_unit.py
```

- [ ] **Step 2: Verify no remaining imports of deleted modules**

```bash
cd backend && grep -r "from app.services.typo" app/ tests/ 2>/dev/null
cd backend && grep -r "from app.bootstrap.runtime_typo" app/ 2>/dev/null
cd backend && grep -r "from app.api.routes.tokens" app/ 2>/dev/null
```

Expected: no output from any of those commands.

- [ ] **Step 3: Run tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete old TypoEngine code (replaced by fuzzy_search)"
```

---

## Task 6: Add `did_you_mean` to API schemas

**Files:**
- Modify: `backend/app/api/schemas/v1/wordbank.py`
- Modify: `frontend/src/app/core/types-api.ts`

- [ ] **Step 1: Update backend schemas**

Open `backend/app/api/schemas/v1/wordbank.py`.

Add `did_you_mean` to `WordbankSearchResponse` (line ~314):

```python
# BEFORE:
class WordbankSearchResponse(BaseModel):
    items: list[WordbankSearchItem]

# AFTER:
class WordbankSearchResponse(BaseModel):
    items: list[WordbankSearchItem]
    did_you_mean: str | None = None
```

Add `did_you_mean` to `CORSearchFormResponse` (line ~347):

```python
# BEFORE:
class CORSearchFormResponse(BaseModel):
    form: str
    groups: list[CORSearchGroup] = Field(default_factory=list)

# AFTER:
class CORSearchFormResponse(BaseModel):
    form: str
    groups: list[CORSearchGroup] = Field(default_factory=list)
    did_you_mean: str | None = None
```

- [ ] **Step 2: Update frontend types**

Open `frontend/src/app/core/types-api.ts`.

Update `WordbankSearchResponse` (line ~208):

```typescript
// BEFORE:
export type WordbankSearchResponse = {
  items: WordbankSearchItem[]
}

// AFTER:
export type WordbankSearchResponse = {
  items: WordbankSearchItem[]
  did_you_mean?: string | null
}
```

Update `CORSearchFormResponse` (line ~241):

```typescript
// BEFORE:
export type CORSearchFormResponse = {
  form: string
  groups: CORSearchGroup[]
}

// AFTER:
export type CORSearchFormResponse = {
  form: string
  groups: CORSearchGroup[]
  did_you_mean?: string | null
}
```

- [ ] **Step 3: Run backend tests to ensure schema serializes correctly**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add backend/app/api/schemas/v1/wordbank.py frontend/src/app/core/types-api.ts
git commit -m "feat: add did_you_mean field to WordbankSearchResponse and CORSearchFormResponse"
```

---

## Task 7: Add fuzzy fallback to wordbank search

**Files:**
- Modify: `backend/app/db/repositories/wordbank_reads.py`
- Modify: `backend/app/services/use_cases/wordbank/queries_lemmas.py`
- Create: `backend/tests/use_cases/test_wordbank_search_typo.py`

- [ ] **Step 1: Write failing tests**

Create `backend/tests/use_cases/test_wordbank_search_typo.py`:

```python
from __future__ import annotations

import pytest

from app.services.use_cases.wordbank import WordbankUseCase
from tests.helpers.factories import _db_path, _cor_local_entry
from tests.helpers.fakes import FakeCORLocalLexiconService
from app.db.migrations import get_connection


def _add_word_directly(db_path, lemma: str) -> None:
    """Insert a minimal lexeme row for testing."""
    with get_connection(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO lexemes (lemma, english_translation) VALUES (?, ?)",
            (lemma, None),
        )


def test_search_returns_did_you_mean_when_typo(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_lemmas("huse")

    assert result.did_you_mean == "hus"
    assert any(item.lemma == "hus" for item in result.items)


def test_search_returns_no_did_you_mean_when_direct_match(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_lemmas("hus")

    assert result.did_you_mean is None
    assert any(item.lemma == "hus" for item in result.items)


def test_search_returns_no_did_you_mean_when_no_correction_found(tmp_path):
    db = _db_path(tmp_path)
    _add_word_directly(db, "hus")
    cor_local = FakeCORLocalLexiconService()
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    # "xyz" has no close wordbank lemma
    result = use_case.search_lemmas("xyz")

    assert result.did_you_mean is None
    assert result.items == []
```

- [ ] **Step 2: Run to verify tests fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_search_typo.py
```

Expected: `AssertionError` — `did_you_mean` is None when it should be "hus".

- [ ] **Step 3: Add `list_all_lemma_strings` to repository**

Open `backend/app/db/repositories/wordbank_reads.py`.

Add this method to `WordbankReadRepository` after `list_lemmas` (around line 90):

```python
def list_all_lemma_strings(self) -> list[str]:
    with timed_db_operation("wordbank.list_all_lemma_strings"), get_connection(
        self._db_path, read_only=True
    ) as conn:
        rows = conn.execute(
            "SELECT lemma FROM lexemes ORDER BY lemma COLLATE NOCASE"
        ).fetchall()
    return [str(row["lemma"]) for row in rows]
```

- [ ] **Step 4: Update `queries_lemmas.py` to use fuzzy fallback**

Open `backend/app/services/use_cases/wordbank/queries_lemmas.py`.

Add import at top:
```python
from app.services.fuzzy_search import fuzzy_suggest
```

Update `search_lemmas`:

```python
def search_lemmas(runtime: WordbankRuntime, query: str, *, limit: int = 8) -> WordbankSearchResponse:
    ensure_wordbank_meaning_compatibility(runtime)
    normalized_query = normalize_token(query)
    if not normalized_query:
        raise ValueError("query is required")
    if limit < 1:
        raise ValueError("limit must be at least 1")

    rows = runtime.repository.search_lemmas(normalized_query, limit=limit)

    did_you_mean: str | None = None
    if not rows:
        all_lemmas = runtime.repository.list_all_lemma_strings()
        suggestions = fuzzy_suggest(normalized_query, all_lemmas)
        if suggestions:
            did_you_mean = suggestions[0]
            rows = runtime.repository.search_lemmas(did_you_mean, limit=limit)

    gloss_translation_cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] = {}

    return WordbankSearchResponse(
        items=[
            WordbankSearchItem(
                lemma=row.lemma,
                display_lemma=_display_lemma_for_list(runtime, row.lemma, row.pos_tag),
                meaning_id=row.meaning_id,
                meaning_key=row.meaning_key,
                gloss=row.gloss,
                gloss_translation=(
                    meaning_gloss_translation(
                        runtime,
                        lexeme_lemma=row.lemma,
                        lexeme_pos_tag=row.pos_tag,
                        meaning_gloss=row.gloss,
                        meaning_translation=row.english_translation,
                        meaning_pos_tag=row.pos_tag,
                        cor_lemma_idx=row.cor_lemma_idx,
                        cache=gloss_translation_cache,
                    )
                    if row.meaning_id is not None
                    else None
                ),
                cor_lemma_idx=row.cor_lemma_idx,
                english_translation=row.english_translation,
                variation_count=row.variation_count,
                match_surface=row.match_surface,
                query_cor_ids=row.query_cor_ids,
                pos_tag=row.pos_tag,
                morphology=row.morphology,
            )
            for row in rows
        ],
        did_you_mean=did_you_mean,
    )
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_search_typo.py
```

Expected: all 3 tests pass.

- [ ] **Step 6: Run full suite**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/repositories/wordbank_reads.py \
        backend/app/services/use_cases/wordbank/queries_lemmas.py \
        backend/tests/use_cases/test_wordbank_search_typo.py
git commit -m "feat: add fuzzy fallback to wordbank search — returns did_you_mean on empty results"
```

---

## Task 8: Add `unique_lemmas` to CORLocalLexiconService and fuzzy fallback to COR search

**Files:**
- Modify: `backend/app/services/cor_local.py`
- Modify: `backend/tests/helpers/fakes.py`
- Modify: `backend/app/services/use_cases/wordbank/collaborators/cor_local.py`
- Modify: `backend/tests/use_cases/test_wordbank_search_typo.py`

- [ ] **Step 1: Extend `test_wordbank_search_typo.py` with COR test**

Append to `backend/tests/use_cases/test_wordbank_search_typo.py`:

```python
def test_cor_search_returns_did_you_mean_when_typo(tmp_path):
    db = _db_path(tmp_path)
    hus_entry = _cor_local_entry(
        cor_id="COR.HUS.LEM",
        lemma="hus",
        gloss="house",
        form="hus",
        lemma_idx=1,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    cor_local = FakeCORLocalLexiconService(
        by_form={"hus": [hus_entry]},
        unique_lemmas=frozenset(["hus"]),
    )
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_cor_form("huse")

    assert result.did_you_mean == "hus"
    assert len(result.groups) > 0
    assert result.groups[0].lemma == "hus"


def test_cor_search_no_did_you_mean_when_direct_match(tmp_path):
    db = _db_path(tmp_path)
    hus_entry = _cor_local_entry(
        cor_id="COR.HUS.LEM",
        lemma="hus",
        gloss="house",
        form="hus",
        lemma_idx=1,
        pos_tag="NOUN",
        morphology="Gender=Neut|Number=Sing|Definite=Ind",
        gram_raw="sb.itk.sg.ubest",
    )
    cor_local = FakeCORLocalLexiconService(
        by_form={"hus": [hus_entry]},
        unique_lemmas=frozenset(["hus"]),
    )
    use_case = WordbankUseCase(db, cor_local_lexicon_service=cor_local)

    result = use_case.search_cor_form("hus")

    assert result.did_you_mean is None
    assert len(result.groups) > 0
```

- [ ] **Step 2: Run to verify new COR tests fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_search_typo.py::test_cor_search_returns_did_you_mean_when_typo
```

Expected: `TypeError` — `FakeCORLocalLexiconService` doesn't accept `unique_lemmas` kwarg yet.

- [ ] **Step 3: Update `FakeCORLocalLexiconService` in `tests/helpers/fakes.py`**

Open `backend/tests/helpers/fakes.py`. Update `FakeCORLocalLexiconService` to accept and expose `unique_lemmas`:

```python
class FakeCORLocalLexiconService:
    def __init__(
        self,
        by_form: dict[str, list[CORLocalEntry]] | None = None,
        by_lemma_idx: dict[int, list[CORLocalEntry]] | None = None,
        unique_lemmas: frozenset[str] | None = None,
    ):
        self._by_form = {key.lower(): value for key, value in (by_form or {}).items()}
        self._by_lemma_idx = by_lemma_idx or {}
        self.unique_lemmas: frozenset[str] = unique_lemmas if unique_lemmas is not None else frozenset()

    # ... rest of methods unchanged
```

- [ ] **Step 4: Add `unique_lemmas` property to real `CORLocalLexiconService`**

Open `backend/app/services/cor_local.py`.

Add `unique_lemmas` lazy property to `CORLocalLexiconService`. Since it's a `@dataclass`, add a private backing field using `field(default=None, init=False, repr=False)`:

```python
from dataclasses import dataclass, field

@dataclass
class CORLocalLexiconService:
    db_path: Path
    provider: str = "cor_local"
    _unique_lemmas: frozenset[str] | None = field(default=None, init=False, repr=False)

    @property
    def unique_lemmas(self) -> frozenset[str]:
        if self._unique_lemmas is None:
            rows = self._query_rows(
                "SELECT DISTINCT lower(lemma) AS lemma FROM cor_entries WHERE norm = 'N'",
                (),
            )
            self._unique_lemmas = frozenset(str(row["lemma"]) for row in rows)
        return self._unique_lemmas
```

Note: `dataclasses.field` is already imported via `from dataclasses import dataclass` — add `field` to the import if not present.

- [ ] **Step 5: Add fuzzy fallback to `collaborators/cor_local.py` `search_cor_form`**

Open `backend/app/services/use_cases/wordbank/collaborators/cor_local.py`.

Add import at top:
```python
from app.services.fuzzy_search import fuzzy_suggest
```

Update `search_cor_form` to use fuzzy fallback when entries are empty. The function currently starts with:
```python
def search_cor_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    translation: TranslationCollaborator,
    form: str,
    *,
    limit: int = 100,
    include_translations: bool = True,
) -> CORSearchFormResponse:
    normalized_form = normalize_token(form)
    if not normalized_form:
        raise ValueError("form is required")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if cor_local_lexicon_service is None:
        raise RuntimeError("COR local lookup service is unavailable.")

    try:
        entries = cor_local_lexicon_service.lookup_form(normalized_form, limit=limit)
    except FileNotFoundError as exc:
        raise RuntimeError(...) from exc
    entries = [entry for entry in entries if entry.norm == "N"]
    entries = consolidate_cor_local_entries(entries)
    entries = drop_glossless_when_gloss_exists(entries)

    groups: list[CORSearchGroup] = []
    ...
    return CORSearchFormResponse(form=normalized_form, groups=groups)
```

Add fuzzy fallback block after the three `entries = ...` lines and before `groups`:

```python
    entries = [entry for entry in entries if entry.norm == "N"]
    entries = consolidate_cor_local_entries(entries)
    entries = drop_glossless_when_gloss_exists(entries)

    did_you_mean: str | None = None
    if not entries:
        suggestions = fuzzy_suggest(normalized_form, cor_local_lexicon_service.unique_lemmas)
        if suggestions:
            did_you_mean = suggestions[0]
            try:
                fallback_entries = cor_local_lexicon_service.lookup_form(did_you_mean, limit=limit)
            except FileNotFoundError:
                fallback_entries = []
            fallback_entries = [e for e in fallback_entries if e.norm == "N"]
            fallback_entries = consolidate_cor_local_entries(fallback_entries)
            fallback_entries = drop_glossless_when_gloss_exists(fallback_entries)
            entries = fallback_entries

    groups: list[CORSearchGroup] = []
    ...
    return CORSearchFormResponse(form=normalized_form, groups=groups, did_you_mean=did_you_mean)
```

- [ ] **Step 6: Run tests to verify new COR tests pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_search_typo.py
```

Expected: all 5 tests pass.

- [ ] **Step 7: Run full suite**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/services/cor_local.py \
        backend/tests/helpers/fakes.py \
        backend/app/services/use_cases/wordbank/collaborators/cor_local.py \
        backend/tests/use_cases/test_wordbank_search_typo.py
git commit -m "feat: add fuzzy fallback to COR form search — returns did_you_mean on empty results"
```

---

## Task 9: Frontend — wire `didYouMean` through hook and show "Did you mean?" item

**Files:**
- Modify: `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
- Modify: `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`
- Modify: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`
- Modify: `frontend/src/test/app/mock-fetch.ts`
- Modify: `frontend/src/test/app/app-shell-search-basics.test.tsx`

- [ ] **Step 1: Add `wordbankSearchHandler` to mock-fetch**

Open `frontend/src/test/app/mock-fetch.ts`.

In the `mockFetchImplementation` options type, add:
```typescript
wordbankSearchHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
```

In the fetch handler block that handles `/api/wordbank/search?` (around line 960), add an early return if `wordbankSearchHandler` is set:
```typescript
if (url.includes("/api/wordbank/search?")) {
  if (options?.wordbankSearchHandler) {
    return options.wordbankSearchHandler(input, init)
  }
  // ... existing filtered logic unchanged
```

- [ ] **Step 2: Write the failing frontend test**

Open `frontend/src/test/app/app-shell-search-basics.test.tsx`.

Add this test inside the `describe("App shell and search", ...)` block:

The test file already imports `responseOf` via `@/test/app-test-helpers` — that export re-exports from `./app/render-helpers`. No additional import needed.

```typescript
it("shows Did you mean suggestion when search returns did_you_mean", async () => {
  mockFetchImplementation({
    wordbankSearchHandler: async (_input, _init) => {
      const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
      const parsed = new URL(url, "http://localhost")
      const query = parsed.searchParams.get("query") ?? ""
      if (query === "huse") {
        return responseOf({
          items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
          did_you_mean: "hus",
        })
      }
      return responseOf({ items: [] })
    },
  })

  renderApp()

  const searchButton = await screen.findByRole("button", { name: /search/i })
  fireEvent.click(searchButton)

  const input = screen.getByRole("combobox", { name: /command search/i })
  fireEvent.change(input, { target: { value: "huse" } })

  await waitFor(() => {
    expect(screen.getByText(/did you mean/i)).toBeInTheDocument()
    expect(screen.getByText(/"hus"/i)).toBeInTheDocument()
  })
})

it("selecting Did you mean replaces the search query", async () => {
  mockFetchImplementation({
    wordbankSearchHandler: async (_input, _init) => {
      const url = typeof _input === "string" ? _input : _input instanceof URL ? _input.toString() : _input.url
      const parsed = new URL(url, "http://localhost")
      const query = parsed.searchParams.get("query") ?? ""
      if (query === "huse") {
        return responseOf({
          items: [],
          did_you_mean: "hus",
        })
      }
      if (query === "hus") {
        return responseOf({
          items: [{ lemma: "hus", display_lemma: "hus", variation_count: 0, english_translation: "house", match_surface: "hus", query_cor_ids: [], meaning_id: null, meaning_key: null, gloss: null, cor_lemma_idx: null }],
          did_you_mean: null,
        })
      }
      return responseOf({ items: [] })
    },
  })

  renderApp()

  const searchButton = await screen.findByRole("button", { name: /search/i })
  fireEvent.click(searchButton)

  const input = screen.getByRole("combobox", { name: /command search/i })
  fireEvent.change(input, { target: { value: "huse" } })

  const suggestion = await screen.findByText(/did you mean/i)
  fireEvent.click(suggestion)

  await waitFor(() => {
    expect(input).toHaveValue("hus")
  })
})
```

- [ ] **Step 3: Run to verify tests fail**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-basics.test.tsx
```

Expected: two new tests fail — the "Did you mean" text is not rendered yet.

- [ ] **Step 4: Update `useSidebarSearch.ts`**

Open `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`.

Add `didYouMean` state and wire it from the wordbank search response:

```typescript
const [didYouMean, setDidYouMean] = useState<string | null>(null)
```

In the wordbank search effect (the `useEffect` around line 67), after `commitSearchMatches(exactMatches)`, also set `didYouMean`:

```typescript
// After setting exactMatches — also track the correction
const correction = payload.did_you_mean ?? null
// When backend returns did_you_mean, items are for the corrected word.
// Use the correction as effective query for matching.
const effectiveQuery = correction ?? normalizedQuery
const exactMatches = (payload.items ?? []).filter((item) => {
  const lemmaKey = normalizeSearchWord(item.lemma)
  const matchSurfaceKey = normalizeSearchWord(item.match_surface ?? "")
  return lemmaKey === effectiveQuery || matchSurfaceKey === effectiveQuery
})
wordbankSearchCacheRef.current.set(normalizedQuery, exactMatches)
commitSearchMatches(exactMatches)
if (!cancelled) {
  setDidYouMean(correction)
}
```

Also reset `didYouMean` when `normalizedQuery` changes and produces direct results (add inside the effect's cleanup or when setting new matches with no correction):

```typescript
// In the early-return branch (no query or cached with no correction):
if (!correction) setDidYouMean(null)
```

And in the cleanup function of the effect:
```typescript
return () => {
  cancelled = true
  window.clearTimeout(timeoutId)
  controller.abort()
}
```

Add `didYouMean` to the returned object:

```typescript
return {
  searchQuery,
  setSearchQuery,
  normalizedQuery,
  matchingNotes,
  searchApiMatches,
  activeCorFormSearchResult,
  isCorTranslationsLoading,
  didYouMean,
}
```

- [ ] **Step 5: Update `SidebarSearchResultsState` and `SidebarSearchResultsActions` in `sidebar-search-results.tsx`**

Open `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`.

Add `didYouMean: string | null` to `SidebarSearchResultsState`:

```typescript
export type SidebarSearchResultsState = {
  normalizedQuery: string
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasNoteResults: boolean
  hasPageResults: boolean
  didYouMean: string | null   // NEW
}
```

Add `onSetSearchQuery` to `SidebarSearchResultsActions`:

```typescript
export type SidebarSearchResultsActions = {
  onOpenSavedNote: (noteId: string) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onAddWordFromSearch: (...) => Promise<string | null>
  onCloseSearch: () => void
  onSetSearchQuery: (query: string) => void   // NEW
}
```

In `SidebarSearchResults` component, add the "Did you mean?" `CommandItem` at the top of `CommandList`, before the wordbank group:

```tsx
export function SidebarSearchResults({ state, data, actions }: SidebarSearchResultsProps) {
  return (
    <CommandList>
      {state.normalizedQuery && !state.hasAnyResults && !state.didYouMean
        ? <CommandEmpty>No results found.</CommandEmpty>
        : null}
      {state.didYouMean ? (
        <>
          <CommandItem
            value="did-you-mean-suggestion"
            onSelect={() => actions.onSetSearchQuery(state.didYouMean!)}
          >
            Did you mean &ldquo;{state.didYouMean}&rdquo;?
          </CommandItem>
          <CommandSeparator />
        </>
      ) : null}
      {/* ... rest unchanged */}
    </CommandList>
  )
}
```

- [ ] **Step 6: Update `app-sidebar.tsx`**

Open `frontend/src/app/chrome/sidebar/app-sidebar.tsx`.

Destructure `didYouMean` from `useSidebarSearch`:

```typescript
const {
  searchQuery,
  setSearchQuery,
  normalizedQuery,
  matchingNotes,
  searchApiMatches,
  activeCorFormSearchResult,
  isCorTranslationsLoading,
  didYouMean,     // NEW
} = useSidebarSearch({...})
```

Add `didYouMean` to `searchResultState`:

```typescript
const searchResultState: SidebarSearchResultsState = {
  normalizedQuery,
  hasAnyResults,
  hasWordbankSectionResults,
  hasWordbankActions,
  hasNoteResults,
  hasPageResults,
  didYouMean,     // NEW
}
```

Add `onSetSearchQuery` to `searchResultActions`:

```typescript
const searchResultActions: SidebarSearchResultsActions = {
  onOpenSavedNote,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onAddWordFromSearch,
  onCloseSearch: () => {
    setIsSearchOpen(false)
    setSearchQuery("")
  },
  onSetSearchQuery: (query: string) => {     // NEW
    setSearchQuery(query)
    setCommandSelectionOverride("")
  },
}
```

- [ ] **Step 7: Run frontend tests**

```bash
cd frontend && npx vitest run src/test/app/app-shell-search-basics.test.tsx
```

Expected: all tests including the two new ones pass.

- [ ] **Step 8: Run full frontend test suite**

```bash
cd frontend && npx vitest run src/test/
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/app/chrome/sidebar/use-sidebar-search.ts \
        frontend/src/app/chrome/sidebar/sidebar-search-results.tsx \
        frontend/src/app/chrome/sidebar/app-sidebar.tsx \
        frontend/src/test/app/mock-fetch.ts \
        frontend/src/test/app/app-shell-search-basics.test.tsx
git commit -m "feat: show Did you mean suggestion in search when typo detected"
```

---

## Task 10: Update API contract documentation

**Files:**
- Modify: `docs/api-contract.md`

- [ ] **Step 1: Update `/api/wordbank/search` entry**

Open `docs/api-contract.md`. Find the section starting at line ~218.

```markdown
### GET `/api/wordbank/search`
- **Request model:** none (`query`, `limit` query params).
- **Response model:** `WordbankSearchResponse`.
- **Notable status/error behavior:** `422` validation failures (empty query, limit out of range). `503` DB unavailable/locked. `503` runtime errors.
- **Field invariants:** saved search rows keep lemma translation + gloss translation separate. `english_translation` = saved lemma translation only. `gloss_translation` = optional disambiguation context. Raw `gloss` not promoted into `english_translation`. `did_you_mean`: non-null when query had no direct matches and a Levenshtein-close wordbank lemma was found; `items` then contains results for the corrected word.
```

- [ ] **Step 2: Update `/api/wordbank/search/cor-form` entry**

Find the section at line ~224. Add `did_you_mean` invariant:

```markdown
### GET `/api/wordbank/search/cor-form`
- **Request model:** none (`form`, `limit`, `include_translations` query params).
- **Response model:** `CORSearchFormResponse`.
- **Notable status/error behavior:** `422` validation failures. `503` DB unavailable/locked. `503` runtime errors.
- **Field invariants:**
  - ... (existing invariants unchanged)
  - `did_you_mean`: non-null when `form` had no COR entries and a Levenshtein-close COR lemma was found; `groups` then contains results for the corrected lemma.
```

- [ ] **Step 3: Run docs smoke**

```bash
make docs-smoke
```

Expected: passes.

- [ ] **Step 4: Commit**

```bash
git add docs/api-contract.md
git commit -m "docs: update api-contract with did_you_mean fields for search endpoints"
```

---

## Final verification

- [ ] **Run full backend suite**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```

- [ ] **Run full frontend suite**

```bash
cd frontend && npx vitest run src/test/
```

- [ ] **Run linting**

```bash
make lint
```

- [ ] **Run maintainability check**

```bash
make maintainability-check
```

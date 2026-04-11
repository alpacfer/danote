# Gemini Auto-Apply + Change History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Auto-apply eligible Gemini verification actions (`fix_translation`, `fix_variations`) without user confirmation, persist every applied change to a new DB table, and expose per-lemma change history with revert support in the verification popover.

**Architecture:** New `verification_change_log` DB table tracks applied actions with before/after snapshots. The `VerificationCollaborator` writes to this table when applying changes and auto-applies eligible actions after verification results are persisted. Two new API endpoints expose change history and revert. The frontend adds a `useVerificationChanges` hook and a "Changes" section in the verification popover.

**Tech Stack:** Python/FastAPI/SQLite (backend), React 19/TypeScript/Tailwind/shadcn (frontend), Vitest/pytest (tests)

---

## File Map

**Create:**
- `backend/migrations/020_verification_change_log.sql`
- `backend/app/db/repositories/wordbank_change_log.py`
- `backend/app/services/use_cases/wordbank/verification_change_log.py`
- `backend/tests/use_cases/test_wordbank_verification_change_log.py`
- `frontend/src/app/hooks/wordbank/use-verification-changes.ts`
- `frontend/src/test/hooks/wordbank/use-verification-changes.test.ts`

**Modify:**
- `backend/app/db/repositories/wordbank_models.py` — add `VerificationChangeLogRecord`
- `backend/app/db/repositories/wordbank.py` — add `WordbankChangeLogRepository` to facade
- `backend/app/api/schemas/v1/wordbank.py` — add 4 new models
- `backend/app/services/use_cases/wordbank/collaborators/verification.py` — DB change log write, auto-apply, new public methods
- `backend/app/services/use_cases/wordbank/core.py` — add `get_verification_changes`, `revert_verification_change`
- `backend/app/api/routes/wordbank.py` — add 2 new routes
- `frontend/src/app/core/types-api.ts` — add 3 new types
- `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx` — add Changes section + new props
- `frontend/src/app/hooks/wordbank/use-verification-workflow.ts` — wire `useVerificationChanges`

---

## Task 1: Migration

**Files:**
- Create: `backend/migrations/020_verification_change_log.sql`

- [ ] **Step 1: Create migration**

```sql
-- backend/migrations/020_verification_change_log.sql
CREATE TABLE IF NOT EXISTS verification_change_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stored_lemma TEXT NOT NULL,
    stored_surface_form TEXT,
    meaning_id INTEGER,
    action_type TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    applied_at TEXT NOT NULL,
    reverted_at TEXT,
    provider TEXT
);

CREATE INDEX IF NOT EXISTS idx_vcl_lemma ON verification_change_log (stored_lemma);
```

- [ ] **Step 2: Verify migration applies**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "
from app.db.migrations import get_connection
import tempfile, pathlib
with tempfile.TemporaryDirectory() as d:
    db = pathlib.Path(d) / 'test.sqlite3'
    with get_connection(db) as conn:
        conn.execute('SELECT id FROM verification_change_log LIMIT 1')
    print('OK')
"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/020_verification_change_log.sql
git commit -m "feat: add verification_change_log migration"
```

---

## Task 2: DB Model + Repository

**Files:**
- Modify: `backend/app/db/repositories/wordbank_models.py`
- Create: `backend/app/db/repositories/wordbank_change_log.py`
- Modify: `backend/app/db/repositories/wordbank.py`

- [ ] **Step 1: Add `VerificationChangeLogRecord` to `wordbank_models.py`**

After the `VerificationRecord` dataclass (around line 132), add:

```python
@dataclass(frozen=True, slots=True)
class VerificationChangeLogRecord:
    id: int
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    action_type: str
    before_json: str
    after_json: str
    applied_at: str
    reverted_at: str | None
    provider: str | None


def verification_change_log_from_row(row) -> VerificationChangeLogRecord:
    return VerificationChangeLogRecord(
        id=int(row["id"]),
        stored_lemma=str(row["stored_lemma"]),
        stored_surface_form=row["stored_surface_form"],
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        action_type=str(row["action_type"]),
        before_json=str(row["before_json"]),
        after_json=str(row["after_json"]),
        applied_at=str(row["applied_at"]),
        reverted_at=row["reverted_at"],
        provider=row["provider"],
    )
```

Also add `VerificationChangeLogRecord` and `verification_change_log_from_row` to the module's `__all__` list at the bottom of the file (or add one if absent — check if there is one first).

- [ ] **Step 2: Create `wordbank_change_log.py`**

```python
from __future__ import annotations

import json
from pathlib import Path

from app.db.repositories.wordbank_models import (
    VerificationChangeLogRecord,
    verification_change_log_from_row,
)
from app.db.sqlite import get_connection, timed_db_operation


class WordbankChangeLogRepository:
    _db_path: Path

    def insert_change_log_entry(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        meaning_id: int | None,
        action_type: str,
        before_json: dict,
        after_json: dict,
        applied_at: str,
        provider: str | None,
    ) -> int:
        with timed_db_operation("wordbank.insert_change_log_entry"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO verification_change_log
                    (stored_lemma, stored_surface_form, meaning_id, action_type,
                     before_json, after_json, applied_at, provider)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    stored_surface_form,
                    meaning_id,
                    action_type,
                    json.dumps(before_json, ensure_ascii=True, sort_keys=True),
                    json.dumps(after_json, ensure_ascii=True, sort_keys=True),
                    applied_at,
                    provider,
                ),
            )
            return int(cursor.lastrowid)

    def get_change_log_entries_for_lemma(
        self,
        stored_lemma: str,
        *,
        limit: int = 50,
    ) -> list[VerificationChangeLogRecord]:
        with timed_db_operation("wordbank.get_change_log_entries_for_lemma"), get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, stored_lemma, stored_surface_form, meaning_id, action_type,
                       before_json, after_json, applied_at, reverted_at, provider
                FROM verification_change_log
                WHERE stored_lemma = ?
                ORDER BY applied_at DESC
                LIMIT ?
                """,
                (stored_lemma, limit),
            ).fetchall()
            return [verification_change_log_from_row(row) for row in rows]

    def get_change_log_entry(self, entry_id: int) -> VerificationChangeLogRecord | None:
        with timed_db_operation("wordbank.get_change_log_entry"), get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id, stored_lemma, stored_surface_form, meaning_id, action_type,
                       before_json, after_json, applied_at, reverted_at, provider
                FROM verification_change_log
                WHERE id = ?
                LIMIT 1
                """,
                (entry_id,),
            ).fetchone()
            return verification_change_log_from_row(row) if row is not None else None

    def set_change_log_reverted(self, entry_id: int, reverted_at: str) -> None:
        with timed_db_operation("wordbank.set_change_log_reverted"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE verification_change_log
                SET reverted_at = ?
                WHERE id = ?
                """,
                (reverted_at, entry_id),
            )
```

- [ ] **Step 3: Add to `wordbank.py` facade**

In `backend/app/db/repositories/wordbank.py`, add import at the top:

```python
from app.db.repositories.wordbank_change_log import WordbankChangeLogRepository
```

Add `WordbankChangeLogRepository` to the `WordbankRepository` class bases (first in the MRO is fine):

```python
class WordbankRepository(
    WordbankChangeLogRepository,
    WordbankCategoryReadRepository,
    WordbankCategoryMutationRepository,
    WordbankReadRepository,
    WordbankMutationRepository,
):
```

Add to `__all__`:
```python
"WordbankChangeLogRepository",
"VerificationChangeLogRecord",
```

- [ ] **Step 4: Verify imports compile**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "from app.db.repositories.wordbank import WordbankRepository, VerificationChangeLogRecord; print('OK')"
```
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add backend/app/db/repositories/wordbank_models.py backend/app/db/repositories/wordbank_change_log.py backend/app/db/repositories/wordbank.py
git commit -m "feat: add VerificationChangeLogRecord and WordbankChangeLogRepository"
```

---

## Task 3: Schema DTOs

**Files:**
- Modify: `backend/app/api/schemas/v1/wordbank.py`

- [ ] **Step 1: Add 4 new models after `ApplyVerificationChangesResponse` (after line 284)**

```python
class VerificationChangeEntry(BaseModel):
    id: int
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    action_type: str
    before_json: dict[str, object]
    after_json: dict[str, object]
    applied_at: str
    reverted_at: str | None
    provider: str | None


class GetVerificationChangesResponse(BaseModel):
    items: list[VerificationChangeEntry]


class RevertVerificationChangeRequest(BaseModel):
    change_id: int
    stored_lemma: str = Field(..., min_length=1)


class RevertVerificationChangeResponse(BaseModel):
    status: Literal["reverted", "already_reverted", "not_found"]
    change_id: int
```

Make sure `dict` imports are available — `from typing import Any` is not needed since `dict[str, object]` works in Python 3.10+. `Literal` is already imported (check the top of the file; if not present, add `from typing import Literal` — but it's almost certainly already there).

- [ ] **Step 2: Verify compile**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "from app.api.schemas.v1.wordbank import VerificationChangeEntry, GetVerificationChangesResponse, RevertVerificationChangeRequest, RevertVerificationChangeResponse; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/schemas/v1/wordbank.py
git commit -m "feat: add verification change log DTOs"
```

---

## Task 4: Use-Case Change Log Logic

**Files:**
- Create: `backend/app/services/use_cases/wordbank/verification_change_log.py`

This module contains the logic to build before-snapshots for the change log and to apply reversions directly to the DB.

- [ ] **Step 1: Write failing tests first**

Create `backend/tests/use_cases/test_wordbank_verification_change_log.py`:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.db.migrations import get_connection
from app.db.repositories.wordbank import WordbankRepository
from app.services.use_cases.wordbank import WordbankUseCase
from app.services.use_cases.wordbank.verification_change_log import (
    build_change_log_before_json,
    query_surface_forms_snapshot,
    revert_fix_translation,
    revert_fix_variations,
)
from tests.helpers.factories import _cor_local_entry, _db_path
from tests.helpers.fakes import (
    FakeCORLocalLexiconService,
    FakeNLPAdapter,
    FakeVerificationService,
)


def _setup_word(db_path: Path, lemma: str = "løbe", translation: str = "to run") -> int:
    use_case = WordbankUseCase(db_path)
    use_case.add_word(
        lemma,
        lemma,
        search_seed={
            "lemma": lemma,
            "surface": lemma,
            "cor_id": f"COR.{lemma.upper()}.1",
            "cor_lemma_idx": 1,
            "meaning_key": lemma,
            "gloss": translation,
            "english_translation": translation,
            "pos_tag": "VERB",
            "morphology": None,
        },
    )
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(lemma)
    assert lexeme is not None
    return lexeme.id


def test_query_surface_forms_snapshot_returns_forms(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _setup_word(db_path, "løbe")
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    forms = query_surface_forms_snapshot(db_path, lexeme_id=lexeme.id, meaning_id=None)
    assert any(f["form"] == "løbe" for f in forms)


def test_build_change_log_before_json_fix_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _setup_word(db_path, "løbe", translation="to run")
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    before = build_change_log_before_json(
        action_type="fix_translation",
        meaning_id=None,
        before_snapshot={"lemma": {"english_translation": "to run"}, "meaning": None},
        pre_apply_surfaces=None,
    )
    assert before["english_translation"] == "to run"
    assert before["action_type"] == "fix_translation"
    assert before["meaning_id"] is None


def test_build_change_log_before_json_fix_variations(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    _setup_word(db_path, "løbe")
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    surfaces = query_surface_forms_snapshot(db_path, lexeme_id=lexeme.id, meaning_id=None)
    before = build_change_log_before_json(
        action_type="fix_variations",
        meaning_id=None,
        before_snapshot={"lemma": {"lemma": "løbe"}, "meaning": None},
        pre_apply_surfaces=surfaces,
    )
    assert before["action_type"] == "fix_variations"
    assert "surface_forms" in before
    assert any(f["form"] == "løbe" for f in before["surface_forms"])


def test_revert_fix_translation_restores_lexeme_translation(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    lexeme_id = _setup_word(db_path, "løbe", translation="to run")
    # Simulate a change: update translation
    with get_connection(db_path) as conn:
        conn.execute(
            "UPDATE lexemes SET english_translation = ? WHERE id = ?",
            ("to walk", lexeme_id),
        )
    # Revert
    revert_fix_translation(
        db_path=db_path,
        stored_lemma="løbe",
        meaning_id=None,
        old_translation="to run",
    )
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    assert lexeme.english_translation == "to run"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_verification_change_log.py
```
Expected: `ImportError` or `ModuleNotFoundError` — the module doesn't exist yet.

- [ ] **Step 3: Implement `verification_change_log.py`**

```python
from __future__ import annotations

import logging
from pathlib import Path

from app.db.migrations import get_connection
from app.db.repositories.wordbank import WordbankRepository

logger = logging.getLogger(__name__)


def query_surface_forms_snapshot(
    db_path: Path,
    *,
    lexeme_id: int,
    meaning_id: int | None,
) -> list[dict[str, object]]:
    """Return all surface forms for a (lexeme_id, meaning_id) scope before a change."""
    with get_connection(db_path) as conn:
        if meaning_id is None:
            rows = conn.execute(
                """
                SELECT form, pos_tag, morphology, cor_id, source, meaning_id
                FROM surface_forms
                WHERE lexeme_id = ? AND meaning_id IS NULL
                ORDER BY id ASC
                """,
                (lexeme_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT form, pos_tag, morphology, cor_id, source, meaning_id
                FROM surface_forms
                WHERE lexeme_id = ? AND meaning_id = ?
                ORDER BY id ASC
                """,
                (lexeme_id, meaning_id),
            ).fetchall()
        return [dict(row) for row in rows]


def build_change_log_before_json(
    *,
    action_type: str,
    meaning_id: int | None,
    before_snapshot: dict[str, object],
    pre_apply_surfaces: list[dict[str, object]] | None,
) -> dict[str, object]:
    """Build a minimal, revertable before-state dict for the change log."""
    if action_type == "fix_translation":
        meaning = before_snapshot.get("meaning")
        lemma_row = before_snapshot.get("lemma") or {}
        if meaning is not None and isinstance(meaning, dict):
            old_translation = meaning.get("english_translation")
        else:
            old_translation = lemma_row.get("english_translation") if isinstance(lemma_row, dict) else None
        return {
            "action_type": "fix_translation",
            "meaning_id": meaning_id,
            "english_translation": old_translation,
        }
    if action_type == "fix_variations":
        return {
            "action_type": "fix_variations",
            "meaning_id": meaning_id,
            "surface_forms": pre_apply_surfaces or [],
        }
    return {"action_type": action_type, "meaning_id": meaning_id}


def revert_fix_translation(
    *,
    db_path: Path,
    stored_lemma: str,
    meaning_id: int | None,
    old_translation: str | None,
) -> None:
    """Restore the english_translation to its pre-apply value."""
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' not found")
    with get_connection(db_path) as conn:
        if meaning_id is not None:
            conn.execute(
                "UPDATE lexeme_meanings SET english_translation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (old_translation, meaning_id),
            )
        else:
            conn.execute(
                "UPDATE lexemes SET english_translation = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (old_translation, lexeme.id),
            )


def revert_fix_variations(
    *,
    db_path: Path,
    stored_lemma: str,
    meaning_id: int | None,
    surface_forms_snapshot: list[dict[str, object]],
) -> None:
    """Restore surface forms to their pre-apply snapshot."""
    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        raise LookupError(f"Lemma '{stored_lemma}' not found")
    with get_connection(db_path) as conn:
        # Delete current surface forms for this scope
        if meaning_id is None:
            conn.execute(
                "DELETE FROM surface_forms WHERE lexeme_id = ? AND meaning_id IS NULL",
                (lexeme.id,),
            )
        else:
            conn.execute(
                "DELETE FROM surface_forms WHERE lexeme_id = ? AND meaning_id = ?",
                (lexeme.id, meaning_id),
            )
        # Re-insert snapshot forms
        for form in surface_forms_snapshot:
            conn.execute(
                """
                INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source, pos_tag, morphology, cor_id, meaning_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lexeme.id,
                    form["form"],
                    form.get("source") or "manual",
                    form.get("pos_tag"),
                    form.get("morphology"),
                    form.get("cor_id"),
                    meaning_id,
                ),
            )
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_verification_change_log.py
```
Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/use_cases/wordbank/verification_change_log.py backend/tests/use_cases/test_wordbank_verification_change_log.py
git commit -m "feat: add verification change log use-case helpers (TDD)"
```

---

## Task 5: Collaborator — DB Change Log Write + New Methods

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/collaborators/verification.py`

The collaborator gets three additions:
1. Write to DB change log inside `apply_verification_changes`
2. New `get_verification_changes(stored_lemma)` method
3. New `revert_verification_change(change_id, stored_lemma)` method

- [ ] **Step 1: Add imports to `collaborators/verification.py`**

At the top of the file (after existing imports), add:

```python
import json as _json  # json is already imported as `json` above — use alias or check
from app.services.use_cases.wordbank.verification_change_log import (
    build_change_log_before_json,
    query_surface_forms_snapshot,
    revert_fix_translation,
    revert_fix_variations,
)
from app.api.schemas.v1.wordbank import (
    GetVerificationChangesResponse,
    RevertVerificationChangeResponse,
    VerificationChangeEntry,
)
```

Note: `json` is already imported in this file. No need to re-import. Check the top of the file and use the existing `json` import.

- [ ] **Step 2: Add `_write_change_log_db_entry` private method**

Add after `_append_gemini_change_log` (around line 424):

```python
def _write_change_log_db_entry(
    self,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    result,
    pre_apply_surfaces: list[dict[str, object]] | None,
    provider_name: str,
    applied_at: str,
) -> None:
    if result.log_payload is None or result.status != "applied":
        return
    action_type = str(result.log_payload.get("action_type", ""))
    if action_type not in {"fix_translation", "fix_variations"}:
        return
    before_json = build_change_log_before_json(
        action_type=action_type,
        meaning_id=meaning_id,
        before_snapshot=dict(result.log_payload.get("before") or {}),
        pre_apply_surfaces=pre_apply_surfaces,
    )
    after_json = dict(result.log_payload.get("after") or {})
    repository = WordbankRepository(self._db_path)
    try:
        repository.insert_change_log_entry(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            meaning_id=meaning_id,
            action_type=action_type,
            before_json=before_json,
            after_json=after_json,
            applied_at=applied_at,
            provider=provider_name,
        )
    except Exception:
        logger.exception("wordbank_change_log_db_write_failed", extra={"stored_lemma": stored_lemma})
```

- [ ] **Step 3: Modify `apply_verification_changes` to capture pre-apply surfaces and write to DB**

In the existing `apply_verification_changes` method, BEFORE the call to `apply_verification_action(...)`, add surface snapshot capture:

```python
# Capture surface forms before action for fix_variations revert support
action_type_str = str(action.get("action_type", ""))
pre_apply_surfaces: list[dict[str, object]] | None = None
if action_type_str == "fix_variations":
    repository = WordbankRepository(self._db_path)
    lexeme = repository.get_lexeme(normalized_lemma)
    if lexeme is not None:
        pre_apply_surfaces = query_surface_forms_snapshot(
            self._db_path,
            lexeme_id=lexeme.id,
            meaning_id=meaning_id,
        )
```

Then AFTER the existing `_append_gemini_change_log(...)` call (around line 326), add:

```python
self._write_change_log_db_entry(
    stored_lemma=normalized_lemma,
    stored_surface_form=normalized_surface,
    meaning_id=meaning_id,
    result=result,
    pre_apply_surfaces=pre_apply_surfaces,
    provider_name=provider_name,
    applied_at=now_utc_iso(),
)
```

- [ ] **Step 4: Add `get_verification_changes` method**

Add after `rethink_categories`:

```python
def get_verification_changes(self, stored_lemma: str) -> GetVerificationChangesResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    repository = WordbankRepository(self._db_path)
    records = repository.get_change_log_entries_for_lemma(normalized_lemma)
    items = [
        VerificationChangeEntry(
            id=r.id,
            stored_lemma=r.stored_lemma,
            stored_surface_form=r.stored_surface_form,
            meaning_id=r.meaning_id,
            action_type=r.action_type,
            before_json=json.loads(r.before_json),
            after_json=json.loads(r.after_json),
            applied_at=r.applied_at,
            reverted_at=r.reverted_at,
            provider=r.provider,
        )
        for r in records
    ]
    return GetVerificationChangesResponse(items=items)
```

- [ ] **Step 5: Add `revert_verification_change` method**

Add after `get_verification_changes`:

```python
def revert_verification_change(
    self,
    change_id: int,
    stored_lemma: str,
) -> RevertVerificationChangeResponse:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        raise ValueError("stored_lemma is required")
    repository = WordbankRepository(self._db_path)
    entry = repository.get_change_log_entry(change_id)
    if entry is None or entry.stored_lemma != normalized_lemma:
        return RevertVerificationChangeResponse(status="not_found", change_id=change_id)
    if entry.reverted_at is not None:
        return RevertVerificationChangeResponse(status="already_reverted", change_id=change_id)

    before = json.loads(entry.before_json)
    if entry.action_type == "fix_translation":
        revert_fix_translation(
            db_path=self._db_path,
            stored_lemma=normalized_lemma,
            meaning_id=entry.meaning_id,
            old_translation=before.get("english_translation"),
        )
    elif entry.action_type == "fix_variations":
        revert_fix_variations(
            db_path=self._db_path,
            stored_lemma=normalized_lemma,
            meaning_id=entry.meaning_id,
            surface_forms_snapshot=before.get("surface_forms", []),
        )
    else:
        return RevertVerificationChangeResponse(status="not_found", change_id=change_id)

    self._nlp.invalidate_pos_cache(normalized_lemma, entry.stored_surface_form)
    repository.set_change_log_reverted(change_id, now_utc_iso())
    return RevertVerificationChangeResponse(status="reverted", change_id=change_id)
```

- [ ] **Step 6: Verify compile**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "from app.services.use_cases.wordbank.collaborators.verification import VerificationCollaborator; print('OK')"
```
Expected: `OK`

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/use_cases/wordbank/collaborators/verification.py
git commit -m "feat: write DB change log in apply_verification_changes, add get/revert methods"
```

---

## Task 6: Auto-Apply After Verification Persist

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/collaborators/verification.py`

Auto-apply triggers after the verification pipeline saves a result with `fix_translation` or `fix_variations` actions.

- [ ] **Step 1: Write failing test for auto-apply**

Add to `backend/tests/use_cases/test_wordbank_verification_change_log.py`:

```python
def test_auto_apply_fix_translation_on_verify(tmp_path: Path) -> None:
    db_path = _db_path(tmp_path)
    use_case = WordbankUseCase(
        db_path,
        verification_service=FakeVerificationService(
            verdict="flagged",
            message="Wrong translation",
            actions=[{"action_type": "fix_translation", "english_translation": "to walk", "reason": "more accurate"}],
        ),
    )
    use_case.add_word(
        "løbe",
        "løbe",
        search_seed={
            "lemma": "løbe",
            "surface": "løbe",
            "cor_id": "COR.LØBE.1",
            "cor_lemma_idx": 1,
            "meaning_key": "løbe",
            "gloss": "to run",
            "english_translation": "to run",
            "pos_tag": "VERB",
            "morphology": None,
        },
    )
    use_case.verify_word("løbe", None)

    repository = WordbankRepository(db_path)
    lexeme = repository.get_lexeme("løbe")
    assert lexeme is not None
    # Translation was auto-applied
    assert lexeme.english_translation == "to walk"
    # Change log was written
    entries = repository.get_change_log_entries_for_lemma("løbe")
    assert len(entries) == 1
    assert entries[0].action_type == "fix_translation"
    assert entries[0].reverted_at is None
```

Note: `FakeVerificationService` currently does not support an `actions` parameter for suggested actions. The next step updates it.

- [ ] **Step 2: Update `FakeVerificationService` to support suggested actions**

In `backend/tests/helpers/fakes.py`, modify `FakeVerificationService.__init__` to accept `actions`:

```python
class FakeVerificationService:
    provider = "gemini"
    reviewer_role = "Professional Danish Language Expert"

    def __init__(
        self,
        verdict: str = "verified",
        message: str = "Entry is consistent.",
        *,
        categories: tuple[str, ...] = (),
        recategorized_categories: tuple[str, ...] | None = None,
        actions: list[dict] | None = None,
    ):
        self._verdict = verdict
        self._message = message
        self._categories = categories
        self._recategorized_categories = recategorized_categories
        self._actions = actions or []
        self.calls = []
        self.category_calls = []

    def verify_word_entry(self, payload):
        self.calls.append(payload)

        class Result:
            def __init__(self, verdict: str, message: str, categories: tuple[str, ...], actions: list[dict]):
                self.verdict = verdict
                self.message = message
                self.categories = categories
                self.actions = actions

        return Result(self._verdict, self._message, self._categories, self._actions)
```

Then check how the verification pipeline uses the result — find where `verdict.actions` or `suggested_actions` is read in `collaborators/verification.py` or `verification_helper_logic.py`. The pipeline reads `completion_review_actions(verdict)` to get actions. Find `completion_review_actions` in `verification_helper_logic.py` and check how it reads actions from the verdict. Update `FakeVerificationService` to match.

- [ ] **Step 3: Find how `completion_review_actions` reads actions**

```bash
cd backend && grep -n "completion_review_actions\|suggested_actions\|\.actions" app/services/use_cases/wordbank/verification_helper_logic.py | head -30
```

Understand the exact attribute name (`verdict.actions` vs `verdict.suggested_actions` etc.) and update `FakeVerificationService.Result` to use it.

- [ ] **Step 4: Run the test to confirm it fails for the right reason**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_verification_change_log.py::test_auto_apply_fix_translation_on_verify
```
Expected: test fails because auto-apply is not yet implemented (translation still "to run", no change log entry).

- [ ] **Step 5: Add `_auto_apply_eligible_actions` to the collaborator**

Add private method in `VerificationCollaborator`:

```python
_AUTO_APPLY_ACTION_TYPES = {"fix_translation", "fix_variations"}

def _auto_apply_eligible_actions(
    self,
    *,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
) -> None:
    """Auto-apply fix_translation and fix_variations actions after verification persists."""
    repository = WordbankRepository(self._db_path)
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return
    record = repository.get_verification_record(
        lexeme_id=lexeme.id,
        meaning_id=meaning_id,
        stored_surface_form=stored_surface_form,
    )
    if record is None or not record.suggested_actions:
        return
    for action in record.suggested_actions:
        action_type = action.get("action_type")
        if action_type not in self._AUTO_APPLY_ACTION_TYPES:
            continue
        try:
            self.apply_verification_changes(
                stored_lemma=stored_lemma,
                stored_surface_form=stored_surface_form,
                meaning_id=meaning_id,
                action=action,
            )
        except Exception:
            logger.exception(
                "wordbank_auto_apply_failed",
                extra={"stored_lemma": stored_lemma, "action_type": action_type},
            )
```

- [ ] **Step 6: Call `_auto_apply_eligible_actions` after persist in `process_queued_verification_if_current`**

In `VerificationCollaborator.process_queued_verification_if_current` (the method in the collaborator, not the standalone function), find where it calls `process_queued_verification_if_current(...)` from `verification_queue.py` and stores the result. After checking `result == "persisted"`, add:

```python
if result == "persisted":
    self._auto_apply_eligible_actions(
        stored_lemma=stored_lemma,
        stored_surface_form=stored_surface_form,
        meaning_id=meaning_id,
    )
```

- [ ] **Step 7: Call `_auto_apply_eligible_actions` after persist in `verify_added_word`**

In `VerificationCollaborator.verify_added_word`, after `self._persist_verification_result(...)` is called (and before building the response), add:

```python
self._auto_apply_eligible_actions(
    stored_lemma=normalized_lemma,
    stored_surface_form=normalized_surface,
    meaning_id=meaning_id,
)
```

- [ ] **Step 8: Run tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/test_wordbank_verification_change_log.py
```
Expected: All tests pass.

- [ ] **Step 9: Run full test suite to check regressions**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/use_cases/
```
Expected: All pass (no regressions).

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/use_cases/wordbank/collaborators/verification.py backend/tests/helpers/fakes.py backend/tests/use_cases/test_wordbank_verification_change_log.py
git commit -m "feat: auto-apply eligible verification actions after persist"
```

---

## Task 7: Core Methods + Route Handlers

**Files:**
- Modify: `backend/app/services/use_cases/wordbank/core.py`
- Modify: `backend/app/api/routes/wordbank.py`

- [ ] **Step 1: Add methods to `WordbankUseCase` in `core.py`**

After `apply_verification_changes` (around line 308):

```python
def get_verification_changes(self, stored_lemma: str) -> GetVerificationChangesResponse:
    return self._runtime.verification.get_verification_changes(stored_lemma)

def revert_verification_change(
    self, change_id: int, stored_lemma: str
) -> RevertVerificationChangeResponse:
    return self._runtime.verification.revert_verification_change(change_id, stored_lemma)
```

Make sure `GetVerificationChangesResponse` and `RevertVerificationChangeResponse` are imported in `core.py`. Find the existing import block from `app.api.schemas.v1.wordbank` and add them.

- [ ] **Step 2: Add routes to `wordbank.py`**

In `backend/app/api/routes/wordbank.py`, add imports for the new schemas at the top (add to the existing import from `app.api.schemas.v1.wordbank`):

```python
GetVerificationChangesResponse,
RevertVerificationChangeRequest,
RevertVerificationChangeResponse,
```

Add two route handlers after the `apply_verification_changes` route (after line 174):

```python
@router.get("/wordbank/lexemes/verification-changes", response_model=GetVerificationChangesResponse)
def get_verification_changes(
    stored_lemma: str = Query(..., min_length=1),
    request: Request = ...,
) -> GetVerificationChangesResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).get_verification_changes(stored_lemma),
        error_log_name="wordbank_db_operational_error",
    )


@router.post("/wordbank/lexemes/revert-verification-change", response_model=RevertVerificationChangeResponse)
def revert_verification_change(
    payload: RevertVerificationChangeRequest,
    request: Request,
) -> RevertVerificationChangeResponse:
    return run_db_operation(
        request,
        lambda: build_wordbank_use_case(request).revert_verification_change(
            payload.change_id,
            payload.stored_lemma,
        ),
        error_log_name="wordbank_db_operational_error",
    )
```

Note: the `Query` import must be present — it's already imported at the top of the routes file (`from fastapi import APIRouter, HTTPException, Query, Request, Response`).

- [ ] **Step 3: Verify compile**

```bash
cd backend && PYTHONPATH=. .venv/bin/python -c "from app.api.routes.wordbank import router; print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Run full backend tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```
Expected: All pass.

- [ ] **Step 5: Update `docs/api-contract.md`**

Add two entries after the existing `POST /api/wordbank/lexemes/apply-verification-changes` entry:

```markdown
### GET `/api/wordbank/lexemes/verification-changes`
- **Request model:** Query param `stored_lemma: str` (required).
- **Response model:** `GetVerificationChangesResponse` — `items: list[VerificationChangeEntry]` newest-first.
- **Notable status/error behavior:** 400 if `stored_lemma` is empty; 503 on DB unavailable.

### POST `/api/wordbank/lexemes/revert-verification-change`
- **Request model:** `RevertVerificationChangeRequest` — `change_id: int`, `stored_lemma: str`.
- **Response model:** `RevertVerificationChangeResponse` — `status: "reverted" | "already_reverted" | "not_found"`, `change_id: int`.
- **Notable status/error behavior:** Returns 200 with `not_found` if entry is absent or belongs to a different lemma; 200 with `already_reverted` if already reverted; 503 on DB unavailable.
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/use_cases/wordbank/core.py backend/app/api/routes/wordbank.py docs/api-contract.md
git commit -m "feat: add get_verification_changes and revert_verification_change endpoints"
```

---

## Task 8: Frontend Types

**Files:**
- Modify: `frontend/src/app/core/types-api.ts`

- [ ] **Step 1: Add 3 new types after `ApplyVerificationChangesResponse`**

```typescript
export type VerificationChangeEntry = {
  id: number
  stored_lemma: string
  stored_surface_form: string | null
  meaning_id: number | null
  action_type: string
  before_json: Record<string, unknown>
  after_json: Record<string, unknown>
  applied_at: string
  reverted_at: string | null
  provider: string | null
}

export type GetVerificationChangesResponse = {
  items: VerificationChangeEntry[]
}

export type RevertVerificationChangeResponse = {
  status: "reverted" | "already_reverted" | "not_found"
  change_id: number
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/core/types-api.ts
git commit -m "feat: add VerificationChangeEntry and related frontend types"
```

---

## Task 9: `useVerificationChanges` Hook

**Files:**
- Create: `frontend/src/app/hooks/wordbank/use-verification-changes.ts`

- [ ] **Step 1: Create the hook**

```typescript
import { useCallback, useEffect, useMemo, useState } from "react"

import {
  createApiClient,
  normalizeSearchWord,
  type GetVerificationChangesResponse,
  type RevertVerificationChangeResponse,
  type VerificationChangeEntry,
} from "@/app/core"
import { toast } from "sonner"

type UseVerificationChangesParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  selectedLemma: string | null
  setWordbankRefreshTick: (updater: (prev: number) => number) => void
}

export function useVerificationChanges({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
}: UseVerificationChangesParams) {
  const [changes, setChanges] = useState<VerificationChangeEntry[]>([])
  const [isLoadingChanges, setIsLoadingChanges] = useState(false)
  const [isRevertingChange, setIsRevertingChange] = useState(false)

  const apiClient = useMemo(
    () => createApiClient({ backendUrl, extractErrorMessage }),
    [backendUrl, extractErrorMessage],
  )

  const lemmaKey = normalizeSearchWord(selectedLemma ?? "")

  const fetchChanges = useCallback(async () => {
    if (!lemmaKey) {
      setChanges([])
      return
    }
    setIsLoadingChanges(true)
    try {
      const payload = await apiClient.getJson<GetVerificationChangesResponse>(
        `/api/wordbank/lexemes/verification-changes?stored_lemma=${encodeURIComponent(lemmaKey)}`,
        "Could not load verification changes.",
      )
      setChanges(payload.items)
    } catch {
      // Non-critical — silently reset
      setChanges([])
    } finally {
      setIsLoadingChanges(false)
    }
  }, [apiClient, lemmaKey])

  useEffect(() => {
    void fetchChanges()
  }, [fetchChanges])

  const revertChange = useCallback(
    async (changeId: number) => {
      if (!lemmaKey) return
      setIsRevertingChange(true)
      try {
        const payload = await apiClient.postJson<RevertVerificationChangeResponse>(
          "/api/wordbank/lexemes/revert-verification-change",
          { change_id: changeId, stored_lemma: lemmaKey },
          "Could not revert change.",
        )
        if (payload.status === "reverted") {
          toast.success("Change reverted.")
          setWordbankRefreshTick((prev) => prev + 1)
          await fetchChanges()
        } else if (payload.status === "already_reverted") {
          toast.error("This change has already been reverted.")
          await fetchChanges()
        } else {
          toast.error("Change not found.")
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : "Could not revert change."
        toast.error(message)
      } finally {
        setIsRevertingChange(false)
      }
    },
    [apiClient, fetchChanges, lemmaKey, setWordbankRefreshTick],
  )

  return { changes, isLoadingChanges, isRevertingChange, revertChange, refreshChanges: fetchChanges }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/hooks/wordbank/use-verification-changes.ts
git commit -m "feat: add useVerificationChanges hook"
```

---

## Task 10: Popover Changes Section + Wiring

**Files:**
- Modify: `frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx`
- Modify: `frontend/src/app/hooks/wordbank/use-verification-workflow.ts`

- [ ] **Step 1: Add new props to `WordbankVerificationPopoverProps`**

In `wordbank-verification-popover.tsx`, extend the props type:

```typescript
type WordbankVerificationPopoverProps = {
  verificationOverview: VerificationOverview
  isApplyingVerificationChanges: boolean
  isRetryingVerification: boolean
  onOpenChange?: (open: boolean) => void
  onApplyVerificationAction: (targetKey: string, actionIndex: number) => void
  onRetryVerificationTarget: (targetKey: string) => void
  // new:
  changes: VerificationChangeEntry[]
  isRevertingChange: boolean
  onRevertChange: (changeId: number) => void
}
```

Add `VerificationChangeEntry` to the imports from `@/app/core`.

- [ ] **Step 2: Add the Changes section inside `WordbankVerificationPopover`**

In the JSX, after the `verifiedTargets.length > 0` block and before the closing `</>`, add the Changes section. Also update the function signature to destructure the new props:

```tsx
export function WordbankVerificationPopover({
  verificationOverview,
  isApplyingVerificationChanges,
  isRetryingVerification,
  onOpenChange,
  onApplyVerificationAction,
  onRetryVerificationTarget,
  changes,
  isRevertingChange,
  onRevertChange,
}: WordbankVerificationPopoverProps) {
```

Inside the scroll area, after the verified section block, add:

```tsx
{changes.length > 0 ? (
  <VerificationSection label="Changes" count={changes.length}>
    {changes.map((change) => (
      <VerificationChangeRow
        key={change.id}
        change={change}
        isRevertingChange={isRevertingChange}
        onRevertChange={onRevertChange}
      />
    ))}
  </VerificationSection>
) : null}
```

- [ ] **Step 3: Add `VerificationChangeRow` component at the bottom of the file**

Add after `VerificationQueuedRow`:

```tsx
function VerificationChangeRow({
  change,
  isRevertingChange,
  onRevertChange,
}: {
  change: VerificationChangeEntry
  isRevertingChange: boolean
  onRevertChange: (changeId: number) => void
}) {
  const actionLabel = change.action_type === "fix_translation"
    ? "Translation fixed"
    : change.action_type === "fix_variations"
      ? "Variations fixed"
      : change.action_type

  const beforeSummary = buildChangeSummary(change)
  const isReverted = change.reverted_at !== null
  const appliedDate = new Date(change.applied_at)
  const timeLabel = isNaN(appliedDate.getTime())
    ? change.applied_at
    : appliedDate.toLocaleDateString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })

  return (
    <Card variant="subtle">
      <CardContent className="space-y-2 px-3 py-3">
        <div className="flex items-start justify-between gap-3">
          <p className="text-sm font-medium">{actionLabel}</p>
          {isReverted ? (
            <Badge variant="secondary">Reverted</Badge>
          ) : null}
        </div>
        {beforeSummary ? (
          <p className="text-muted-foreground text-sm">{beforeSummary}</p>
        ) : null}
        <p className="text-muted-foreground text-xs">{timeLabel}</p>
        {!isReverted ? (
          <Button
            type="button"
            size="sm"
            variant="outline"
            disabled={isRevertingChange}
            onClick={() => onRevertChange(change.id)}
          >
            {isRevertingChange ? "Reverting..." : "Revert"}
          </Button>
        ) : null}
      </CardContent>
    </Card>
  )
}

function buildChangeSummary(change: VerificationChangeEntry): string | null {
  if (change.action_type === "fix_translation") {
    const before = change.before_json["english_translation"]
    const after = (change.after_json["meaning"] as Record<string, unknown> | null)?.["english_translation"]
      ?? (change.after_json["lemma"] as Record<string, unknown> | null)?.["english_translation"]
    if (before != null && after != null) {
      return `"${String(before)}" → "${String(after)}"`
    }
  }
  if (change.action_type === "fix_variations") {
    const afterForms = change.after_json["surface_forms"] as unknown[] | null
    if (Array.isArray(afterForms) && afterForms.length > 0) {
      return `${afterForms.length} form${afterForms.length === 1 ? "" : "s"} updated`
    }
  }
  return null
}
```

Note: `VerificationChangeEntry` must be imported from `@/app/core`. The `Badge` component is already imported. Verify all imports are present at the top.

- [ ] **Step 4: Wire `useVerificationChanges` into `use-verification-workflow.ts`**

In `use-verification-workflow.ts`, add the import:

```typescript
import { useVerificationChanges } from "@/app/hooks/wordbank/use-verification-changes"
```

Add `useVerificationChanges` to the params type:

```typescript
// The hook already receives backendUrl, extractErrorMessage, selectedLemma, setWordbankRefreshTick
// No new params needed — useVerificationChanges uses the same ones
```

Inside the `useVerificationWorkflow` function body, add:

```typescript
const {
  changes,
  isLoadingChanges,
  isRevertingChange,
  revertChange,
  refreshChanges,
} = useVerificationChanges({
  backendUrl,
  extractErrorMessage,
  selectedLemma,
  setWordbankRefreshTick,
})
```

Add these to the return object:

```typescript
return {
  // ... existing fields ...
  changes,
  isLoadingChanges,
  isRevertingChange,
  revertChange,
  refreshChanges,
}
```

- [ ] **Step 5: Find where `WordbankVerificationPopover` is rendered and pass new props**

```bash
grep -rn "WordbankVerificationPopover" frontend/src/
```

Find the call site (likely a section component). Pass the new props:

```tsx
<WordbankVerificationPopover
  // ... existing props ...
  changes={changes}
  isRevertingChange={isRevertingChange}
  onRevertChange={revertChange}
/>
```

- [ ] **Step 6: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors.

- [ ] **Step 7: Run frontend tests**

```bash
cd frontend && npx vitest run
```
Expected: All pass.

- [ ] **Step 8: Run full backend tests**

```bash
cd backend && PYTHONPATH=. .venv/bin/pytest -q tests/
```
Expected: All pass.

- [ ] **Step 9: Run lint**

```bash
cd /path/to/repo && make lint
```
Expected: No errors.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/app/sections/wordbank/wordbank-verification-popover.tsx frontend/src/app/hooks/wordbank/use-verification-workflow.ts
git commit -m "feat: add Changes section to verification popover with revert support"
```

---

## Task 11: Smoke Test + Docs Sync

- [ ] **Step 1: Run docs smoke**

```bash
make docs-smoke
```
Expected: Passes.

- [ ] **Step 2: Run full suite**

```bash
make test
```
Expected: All pass.

- [ ] **Step 3: Update `docs/versions.md` if any new dependency was added**

Check `git diff HEAD -- backend/requirements*.txt frontend/package.json`. If nothing changed, skip.

- [ ] **Step 4: Final commit if anything was missed**

```bash
git status
```
If any tracked files have uncommitted changes, commit them.

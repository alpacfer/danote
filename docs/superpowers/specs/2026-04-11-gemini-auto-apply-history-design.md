# Gemini Auto-Apply + Change History Design

**Date:** 2026-04-11
**Status:** Approved

## Summary

When Gemini verification produces `fix_translation` or `fix_variations` suggested actions, apply them automatically without user confirmation. Record every auto-applied change in a new DB table. Expose a per-lemma change history with revert support in the verification popover.

---

## Section 1: Auto-apply

### Scope

| Action type | Behaviour |
|---|---|
| `fix_translation` | Auto-applied silently |
| `fix_variations` | Auto-applied silently |
| `move_to_meaning_section` | Manual review (unchanged) |
| `move_to_lemma` | Manual review (unchanged) |

### Flow

1. Verification worker saves result with suggested actions.
2. If all suggested actions are `fix_translation` or `fix_variations`, apply them immediately in the same pipeline step.
3. Write each applied action to `verification_change_log` (section 2).
4. Mark verification target as `verified`.
5. Frontend polls → sees `verified` directly, never a `flagged`/review state for these action types.

If a result has mixed action types (eligible + ineligible), only the eligible ones are auto-applied; the remainder still appear in "Needs review".

### Discovery

No auto-apply toast. Users discover applied changes via the history section in the verification popover. The "Checked" section already signals the target passed.

---

## Section 2: Change log DB table + API

### Migration: `017_verification_change_log.sql`

```sql
CREATE TABLE verification_change_log (
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
CREATE INDEX idx_vcl_lemma ON verification_change_log (stored_lemma);
```

`before_json` / `after_json` reuse the existing snapshot shape already produced by `verification_actions.py` (the same `before`/`after` fields currently written to JSONL). No new serialization logic.

The existing `gemini-applied-changes.jsonl` is kept as an audit trail and is not removed.

### New endpoint: `GET /api/wordbank/lexemes/verification-changes`

Query param: `stored_lemma` (required).

Response: list of entries, newest first.

```json
[
  {
    "id": 42,
    "stored_lemma": "løbe",
    "stored_surface_form": null,
    "meaning_id": 7,
    "action_type": "fix_translation",
    "before_json": {"english_translation": "to run fast"},
    "after_json": {"english_translation": "to run"},
    "applied_at": "2026-04-11T10:23:00Z",
    "reverted_at": null,
    "provider": "gemini"
  }
]
```

### New endpoint: `POST /api/wordbank/lexemes/revert-verification-change`

Request:

```json
{ "change_id": 42, "stored_lemma": "løbe" }
```

Steps:
1. Validate entry exists and belongs to `stored_lemma`.
2. Validate entry is not already reverted (`reverted_at` is null).
3. Apply `before_json` values back to the DB (direct field restore — no need to go through the full verification action pipeline).
4. Set `reverted_at` to current UTC timestamp.
5. Return updated entry.

---

## Section 3: Frontend history + revert UI

### New hook: `useVerificationChanges`

File: `frontend/src/app/hooks/wordbank/use-verification-changes.ts`

Responsibilities:
- Fetch `GET /api/wordbank/lexemes/verification-changes?stored_lemma=X` when lemma changes.
- Expose `changes`, `isLoading`, `revertChange(changeId)`.
- `revertChange` calls the POST revert endpoint, then re-fetches changes and triggers `setWordbankRefreshTick`.

### Verification popover changes

New "Changes" section added to `WordbankVerificationPopover`, below "Checked" and above the provider footer. Only shown when `changes.length > 0`.

Each row:
- Action type label: `"Translation fixed"` / `"Variations fixed"`
- Before → after summary: `"to run fast" → "to run"` (for `fix_translation`)
- Relative timestamp: `"2 hours ago"`
- "Revert" button — disabled + labelled "Reverted" if `reverted_at` is set

New props added to `WordbankVerificationPopoverProps`:
- `changes: VerificationChangeEntry[]`
- `isLoadingChanges: boolean`
- `isRevertingChange: boolean`
- `onRevertChange: (changeId: number) => void`

### Wiring

`use-verification-workflow` composes `useVerificationChanges` and passes its outputs through to the popover. This keeps the popover a pure render component.

### File size

`wordbank-verification-popover.tsx` is currently 282 lines. The changes section adds ~50 lines, staying well under 450.

---

## Architecture layers (edit sequence)

1. Migration SQL
2. DB repository method (insert/query/update `verification_change_log`)
3. Schema DTOs (`VerificationChangeEntry`, `RevertVerificationChangeRequest`, `RevertVerificationChangeResponse`)
4. Use-case: auto-apply in verification pipeline + new `get_verification_changes` + `revert_verification_change`
5. Route handlers (thin wiring)
6. Frontend: `useVerificationChanges` hook
7. Frontend: popover props + rendering

---

## Out of scope

- Revert-of-revert (multi-level undo)
- Global change log view (history is per-lemma only)
- Auto-apply for `move_to_meaning_section` / `move_to_lemma`
- Migration of existing JSONL entries into DB

# Playground section behavior

Retired behavior reference for the previous playground UI: editor, token/phrase popovers, save dialog.

Playground is currently inaccessible from the frontend. It is not in sidebar navigation, command search, hotkeys, or `SectionContent`, and it should not be used while the DaCy NLP stack is retired.

## 1) Entry points and ownership

### Main composition path

- Active app-shell composition no longer assembles Playground props or hooks.
- `PlaygroundSection` = thin, renders three UI subcomponents + `NotesEditor`.

### UI ownership

- `frontend/src/app/sections/playground-section.tsx`
  - Renders: `PlaygroundSaveDialog`, `PlaygroundPhrasePopover`, `PlaygroundHighlightPopover`, `NotesEditor`
  - Displays `noteText.length` char count + section-level analysis error.
- `frontend/src/app/sections/playground/playground-highlight-popover.tsx` — token popover body + actions.
- `frontend/src/app/sections/playground/playground-phrase-popover.tsx` — phrase popover + sentencebank action.
- `frontend/src/app/sections/playground/playground-save-dialog.tsx` — save/create dialog + submit/cancel.
- `frontend/src/components/notes-editor.tsx` — Tiptap lifecycle, text sync, highlight clicks, delayed selection-settle.

### Retired hooks

The previous Playground controller composition and prop adapter files have been removed from the active app-shell path.

## 2) Analysis lifecycle

### Debounce timing

- Debounce: `ANALYZE_DEBOUNCE_MS = 450` ms.
- Input preprocessed via `finalizedAnalysisText()`: trailing whitespace → token complete → analyze; no trailing whitespace → drop trailing in-progress word.

### Abort/cancel and stale-request rules

- `useAnalysis` keeps `activeControllerRef` (abort in-flight) + `latestRequestIdRef` (guard out-of-order).
- New request → abort previous. Only matching `requestId` updates tokens/error. Unmount → abort active.

### Empty-input handling

- Empty finalized input → abort request → clear tokens + error in queued timeout.

### Loading/error rendering

- No global spinner for `/api/analyze`.
- Failure → `analysisError` shown under editor (destructive alert).
- Success → `noteHighlights` recomputed from `noteText + tokens`.

## 3) Highlight interaction rules

### Clickable vs ignored

- Clickable classifications: `known`, `new`, `variation`, `typo_likely`.
- Clicks captured from `mark.clickable-word[data-token-index]`.

- Ignored (no highlight/popover): `PROPN`, `NUM`.
- `openHighlightPopover` exits early for `typo_likely`, `PROPN`, `NUM`.

Result: typo_likely/PROPN/NUM tokens never open popovers or trigger token translation.

## 4) Token popover actions (add/open)

### Open behavior

- Click highlight → `openHighlightPopover(tokenIndex, coords...)`.
- Anchor side via `preferredPopoverSide` viewport heuristic.
- Opening token popover closes phrase popover.
- Token translation requested unless cache has non-null value for token key.

### Primary action behavior

- `open_wordbank`: eye icon, disabled when lemma missing → closes popover → navigates to Wordbank lemma.
- `add_as_new`/`add_variation`: retired with the inaccessible Playground UI.

### Optimistic vs post-response

- Add-to-wordbank is **not optimistic** for classification.
- On API success: success toast, verification/pronunciation background jobs, feedback posted, refresh ticks (`analysis` + `wordbank`). This is historical behavior only.
- On error: error toast, loading key cleared in `finally`.

### Toast/error semantics

- Success: `toast.success(payload.message)`.
- Failure: `toast.error(error.message || fallback)`.

## 5) Phrase popover + sentencebank add

### Selection normalization + eligibility

- Editor selection settles after 180 ms (`scheduleSelectionSettled`).
- Text normalized (`\s+` collapse + trim).
- Phrase popover opens only if normalized selection has `hasMultipleWords`.
- Single-word/empty → close popover, reset phrase translation progress.

### Phrase translation behavior

- Request starts after `PHRASE_TRANSLATION_DELAY_MS = 1000` ms.
- Cached phrase key → no new request.
- Delay timer cleared on reset/unmount.
- Only latest phrase key updates loading/error guards.

### Sentencebank add + duplicate prevention

- `addSentenceToSentencebank` re-normalizes before save.
- Save skipped when: empty/single-word, or phrase already in sentence list (keyed by normalized phrase).
- During save: button disabled via `isSavingSentence`. Also disabled when `isSelectedPhraseSaved`.
- Success → toast, sentencebank refresh tick, `onSentenceSaved` closes popover.
- Failure → error toast.

## 6) Save dialog behavior

### Validation

- Name trimmed on submit. Empty → `toast.error("Note name is required.")`, no save.

### Create/update behavior

- Modes: `initial` (save current), `create_new` (save current silently, create/activate empty note).
- Duplicate detection: case-insensitive trimmed name.
- Duplicate in `initial` → conflict message → "Overwrite existing" option (save with existing note id).
- Duplicate in `create_new` → conflict message → "Use existing note" option (switch active note).

### Close/reset rules

- Open dialog → reset mode, pre-fill `noteNameDraft` to `Note N`, clear conflict.
- Input change → clear conflict. Close/cancel → clear conflict.
- Successful save/create/resolution → close dialog.

## 7) Keyboard/focus behavior

- Highlight click → force Tiptap selection to location → `view.focus()`.
- Popovers prevent auto-focus: `onOpenAutoFocus={(e) => e.preventDefault()}`.
- Typing → `onNoteTextChange` → clears playground transient state (both popovers + transient translation errors) → dismisses popovers.
- Phrase popover dismissal: selection cleared, not multi-word, external close.
- Highlight popover dismissal: external close, note text change, phrase popover opens.

## 8) Empty/error states and character count

### Character count

- Count = raw `noteText.length`, bottom-right editor overlay.

### Empty states

- Editor placeholder: `Type lesson notes here...`.
- Token/phrase popover translation absent: `No translation available.`.

### Error states

- Analysis error → alert paragraph under editor.
- Token/phrase translation failure → inline destructive text in popover.

## 9) Test coverage map

The active `app-playground-*.test.tsx` suite has been retired with the inaccessible UI. Current coverage asserts the shell no longer exposes Playground navigation and saved notes do not open into Playground.

## Documentation parity

- This file documents playground behavior details for this change.

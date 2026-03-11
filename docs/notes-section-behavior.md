# Notes section behavior

This document describes how the Notes section is wired in the app shell and what behavior users should expect when browsing/opening saved notes.

## Entry points

### Section component

- Primary renderer: `frontend/src/app/sections/notes-section.tsx`.
- Props:
  - `savedNotes: SavedNote[]`
  - `onOpenSavedNote: (note: SavedNote) => void`
- The section is purely presentational: it renders the list state and delegates selection behavior to `onOpenSavedNote`.

### App controller + adapter path

Saved-note open behavior is composed through these layers:

1. `useAppController` builds section props with `buildNotesSectionProps` and passes `workspace.openSavedNoteInPlayground` as the open handler.
2. `buildNotesSectionProps` adapts `openSavedNoteInPlayground` to the component prop name `onOpenSavedNote`.
3. `NotesSection` calls `onOpenSavedNote(note)` on card click.
4. `openSavedNoteInPlayground` (from `useNoteWorkspace`) performs the state transition to reopen the selected note in Playground.

Related open-by-id entry point:

- `workspace.openSavedNoteById(noteId)` resolves a note from `savedNotes` and forwards to `openSavedNoteInPlayground`.
- `useAppController` exposes this as `openSavedNoteById` for shell-level surfaces (for example command/search results).

## Rendering states

### Empty state

If `savedNotes.length === 0`, the section shows:

- `No saved notes yet. Save one from Playground.`

No cards are rendered in this branch.

### Card grid layout

When notes exist, cards render in a responsive grid:

- Base: single column (implicit grid with `gap-3`)
- `md` breakpoint: 2 columns (`md:grid-cols-2`)
- `xl` breakpoint: 3 columns (`xl:grid-cols-3`)

Each card is a full-width clickable button nested in a `Card` container.

### Note preview truncation

Preview text uses `previewText(note.text)`:

- Input text is normalized by collapsing whitespace and trimming.
- Empty/whitespace-only text falls back to `No text saved.`
- Default max length is 180 chars.
- Longer text is truncated to `maxLength - 1` chars and suffixed with `...`.

## Timestamp formatting contract

### Source field

- Notes section timestamp source is `SavedNote.savedAt`.
- The field is written as ISO timestamp strings (for example in save flows and autosave).

### Formatter + usage path

- Formatter: `formatSavedNoteTimestamp(value: string)` in `frontend/src/app/core/storage.ts`.
- Path to Notes section rendering:
  1. `NotesSection` reads `note.savedAt`.
  2. Calls `formatSavedNoteTimestamp(note.savedAt)`.
  3. If `savedAt` parses as a valid date, renders locale-formatted medium date + short time.
  4. If parsing fails, renders the original raw string as fallback.

## Open-note flow (selecting a note)

When a user selects a note card (or opens by id through shell search), `openSavedNoteInPlayground` applies the selected note to editor/runtime state:

- Editor content: `setNoteText(note.text)`
- Token analysis payload: `setTokens(note.tokens)`
- Discovered metadata memory: `setDiscoveredTokenMetadata(note.discoveredTokenMetadata)`
- Generated translation cache: `setGeneratedTranslationMap(note.generatedTranslationMap)`
- Clears transient analysis error: `setAnalysisError(null)`
- Clears transient playground popover state: `clearPlaygroundTransientState()`
- Active saved note identity: `setActiveNoteId(note.id)`
- Autosave status: `setAutosaveStatus("saved")`
- Active section: `setActiveSection("playground")`

Net effect: selecting a note always navigates to Playground with that note loaded as the active autosave target.

## Interaction with autosave + save dialog status

- Autosave state labels are derived in `useAppController`:
  - `saving` -> `Autosaving...`
  - `saved` -> `Autosaved`
  - `off` -> `Autosave off`
- Reopening a note sets status to `saved` immediately (before further edits schedule autosave).
- If there is no active saved note id/name, autosave hook turns autosave `off` and clears any pending timeout.
- Save dialog mode is independent UI state (`initial`/`create_new`) in workspace logic:
  - Opened from Playground actions.
  - Notes-section note-open action does not open/close the save dialog directly.
  - On note open, users return to Playground where Save/Create New Note actions reflect active note context.

## Error and fallback behavior

- Notes section open handlers are intentionally non-throwing.
- `openSavedNoteById` is a safe no-op if note id is not found.
- Timestamp formatting falls back to raw `savedAt` string when date parsing fails.
- Preview fallback for blank note text is `No text saved.`
- Saved notes loading from localStorage is defensive: invalid/malformed payloads resolve to `[]`.

## Test mapping

### Primary notes-section behavior test

- `frontend/src/test/app/app-notes.test.tsx`
  - Saves a named note from Playground and verifies autosave status label.
  - Verifies notification entry for save event.
  - Navigates to Notes section, confirms saved card presence + preview content.
  - Clicks saved note card and confirms return to Playground with editor content restored.

### App-shell open-note coverage

- `frontend/src/test/app/app-shell-search-basics.test.tsx`
  - Seeds saved notes, opens command dialog search, selects saved-note result.
  - Verifies app returns to Playground and editor is populated from the saved note.
  - This indirectly covers `openSavedNoteById -> openSavedNoteInPlayground` shell-level path.

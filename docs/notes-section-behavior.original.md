# Notes section behavior deep dive

This document describes the current, exact behavior of the **Notes section** in the frontend UI, including section entry, saved-note visibility, search filtering, opening notes into Playground, and save/new-note flows.

## Entry points and ownership

- App-level section routing and top-level composition: `frontend/src/App.tsx`
- App orchestration root for section props and workspace actions: `frontend/src/app/hooks/app/use-app-controller.ts`
- Foundation wiring for notes persistence + section navigation: `frontend/src/app/hooks/app/controller/use-app-foundation.ts`
- Notes persistence state + local storage sync: `frontend/src/app/hooks/use-notes-persistence.ts`
- Note workspace/save dialog/new-note workflows: `frontend/src/app/hooks/use-note-workspace.ts`
- Debounced autosave for active saved note: `frontend/src/app/hooks/use-note-autosave.ts`
- Notes section adapter and rendering:
  - `frontend/src/app/sections/notes-section-props.ts`
  - `frontend/src/app/sections/notes-section.tsx`
- Sidebar note search/filtering and open actions:
  - `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
  - `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`
  - `frontend/src/app/chrome/sidebar/app-sidebar.tsx`

## Open notes view workflow

Notes can be opened from multiple user paths:

1. Sidebar navigation button (`Notes`) switches `activeSection` to `notes`.
2. Keyboard shortcut (`Alt+N`) triggers the same section selection.
3. Command palette (`Search words and notes...`) "Pages" group can select `Notes`.

When `activeSection === "notes"`, `SectionContent` renders `NotesSection` with props built by `buildNotesSectionProps`.

## Saved note listing and filtering behavior

## Notes section list

`NotesSection` renders one card per saved note from `savedNotes` (most-recent-first ordering as provided by state mutation paths). Each card shows:

- note name
- formatted save timestamp
- shortened preview text

If there are no saved notes, the empty-state message is:

- `No saved notes yet. Save one from Playground.`

## Sidebar filtering (cross-section)

Saved notes are also filterable in sidebar command search:

- `useSidebarSearch` normalizes the query and filters `savedNotes` by:
  - note name includes query, or
  - note text includes query
- Matching notes appear under a `Notes` command group.
- Selecting a filtered note runs `onOpenSavedNote(note.id)` and closes search.

This filtering is available regardless of current section and serves as a quick open flow for Notes/Playground.

## Open note into Playground workflow

Opening a saved note (from Notes cards or sidebar search) calls workspace open handlers that:

1. Hydrate editor state from the saved note (`text`, `tokens`, discovered metadata, translation map).
2. Clear transient Playground state and analysis error.
3. Set the opened note as active (`activeNoteId`).
4. Set autosave status to `saved`.
5. Force `activeSection` to `playground`.

Result: selecting a note always navigates into Playground editing context; Notes acts as a launch/list surface.

## Save-as / new note behavior

## Save dialog mode selection

Opening save dialog uses mode:

- `initial` when there is no active saved note.
- `create_new` when an active saved note already exists.

The dialog name draft defaults to `Note <savedNotes.length + 1>`.

## Save current note

`saveCurrentNote` behavior:

- Name is required.
- Duplicate name checks are case-insensitive (trim + `toLocaleLowerCase`).
- If duplicate exists, dialog enters duplicate-conflict state (no save yet).
- Otherwise updates existing note (or creates one if needed), writes latest editor payload, marks active note, sets autosave `saved`, and closes dialog.
- Non-silent saves show toast + notification.

## Create new named note (save-as new)

`createNewNamedNote` behavior:

- Name is required + duplicate-checked.
- If a note is currently active, pending autosave timeout is cleared and current active note is silently saved first.
- Creates a brand-new saved note with empty content and fresh id.
- Sets new note active, clears editor/analyzed/transient state, sets autosave `saved`, closes dialog, and emits success toast + notification.

## Duplicate-name conflict resolution

When duplicate conflict is resolved:

- In `create_new` mode, existing duplicate note is opened as active note for future autosave.
- In normal save path, save operation can target the existing duplicate note id.

## Rename / delete behavior status

There is currently **no dedicated rename or delete workflow** for saved notes in the Notes section or sidebar UI.

- Rename is only implicitly possible by saving note content with a different name through save dialog conflict paths.
- Deletion controls are not exposed in current Notes/Playground orchestration.

## State-transition notes (section, active note, breadcrumb/title)

## Active section transitions

- `selectNotes()` sets `activeSection = "notes"` and clears Wordbank selection context.
- `openSavedNoteInPlayground()` sets `activeSection = "playground"`.
- App body chooses section component strictly from `activeSection`.

## Active note transitions

- `setActiveNoteId(note.id)` occurs on save, new-note creation, open note, and duplicate-conflict resolution paths.
- `activeSavedNote` is derived from (`savedNotes`, `activeNoteId`) in persistence state.
- Autosave runs only when active note id + active note name are both present; otherwise autosave status is `off`.

## Breadcrumb/title effects

`AppBreadcrumb` behavior:

- In Notes section: title is always `Notes`.
- In Playground: title is active saved note name when present, otherwise `Playground`.

This means opening a note from Notes (or sidebar search) immediately changes breadcrumb label from `Notes` to the note name (or Playground fallback).

## Behavioral test coverage map

Notes workflows are covered primarily through app integration tests under:

- `frontend/src/test/app/`

(Examples include save/open/autosave/sidebar search orchestration tests that exercise `use-app-controller` and workspace/persistence composition.)

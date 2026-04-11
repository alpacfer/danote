# Notes section behavior

## Entry points and ownership

- App routing/composition: `frontend/src/App.tsx`
- Section props + workspace actions: `frontend/src/app/hooks/app/use-app-controller.ts`
- Notes persistence + nav wiring: `frontend/src/app/hooks/app/controller/use-app-foundation.ts`
- Persistence state + localStorage sync: `frontend/src/app/hooks/use-notes-persistence.ts`
- Workspace/save/new-note flows: `frontend/src/app/hooks/use-note-workspace.ts`
- Debounced autosave: `frontend/src/app/hooks/use-note-autosave.ts`
- Section adapter/rendering:
  - `frontend/src/app/sections/notes-section-props.ts`
  - `frontend/src/app/sections/notes-section.tsx`
- Sidebar search/filter + open actions:
  - `frontend/src/app/chrome/sidebar/use-sidebar-search.ts`
  - `frontend/src/app/chrome/sidebar/sidebar-search-results.tsx`
  - `frontend/src/app/chrome/sidebar/app-sidebar.tsx`

## Open notes view workflow

Entry paths:
1. Sidebar `Notes` button → `activeSection = "notes"`
2. `Alt+N` → same
3. Command palette "Pages" group → `Notes`

`activeSection === "notes"` → `SectionContent` renders `NotesSection` via `buildNotesSectionProps`.

## Saved note listing and filtering

### Notes section list

`NotesSection` renders one card per `savedNotes` (most-recent-first). Each card shows: name, formatted save timestamp, shortened preview text. Empty state: `No saved notes yet. Save one from Playground.`

### Sidebar filtering (cross-section)

`useSidebarSearch` normalizes query, filters `savedNotes` by name or text match. Matches appear under `Notes` command group. Selecting → `onOpenSavedNote(note.id)` + close search. Available regardless of active section.

## Open note into Playground

Opening a saved note (cards or sidebar) → workspace open handlers:
1. Hydrate editor from saved note (`text`, `tokens`, metadata, translation map)
2. Clear transient Playground state + analysis error
3. Set `activeNoteId`
4. Set autosave `saved`
5. Force `activeSection = "playground"`

Result: selecting a note always navigates to Playground; Notes is a launch/list surface.

## Save-as / new note behavior

### Save dialog mode

- `initial` when no active saved note
- `create_new` when active saved note exists
- Default name draft: `Note <savedNotes.length + 1>`

### Save current note

`saveCurrentNote`: name required. Duplicate check case-insensitive (trim + `toLocaleLowerCase`). Duplicate → conflict state (no save). Otherwise update/create note, write editor payload, mark active, set autosave `saved`, close dialog. Non-silent saves → toast + notification.

### Create new named note

`createNewNamedNote`: name required + duplicate-checked. If active note exists, clear pending autosave + silently save current. Create new note (empty content, fresh id), set active, clear editor/analyzed/transient state, set autosave `saved`, close dialog, emit success toast + notification.

### Duplicate-name conflict resolution

`create_new` mode → existing duplicate opened as active for future autosave. Normal save → can target existing duplicate note id.

## Rename / delete

**No dedicated rename or delete workflow.** Rename only implicit via save dialog conflict paths. Deletion not exposed.

## State transitions (section, active note, breadcrumb)

### Active section

- `selectNotes()` → `activeSection = "notes"`, clear Wordbank context
- `openSavedNoteInPlayground()` → `activeSection = "playground"`
- App body renders section from `activeSection` only

### Active note

- `setActiveNoteId(note.id)` on save, new-note, open, duplicate resolution
- `activeSavedNote` derived from (`savedNotes`, `activeNoteId`)
- Autosave runs only when `activeNoteId` + `activeNoteName` both present; otherwise status `off`

### Breadcrumb/title

`AppBreadcrumb`: Notes section → title `Notes`. Playground → active note name if present, else `Playground`. Opening note from Notes/sidebar changes breadcrumb from `Notes` to note name (or `Playground` fallback).

## Behavioral test coverage

`frontend/src/test/app/` — save/open/autosave/sidebar search integration tests exercising `use-app-controller` + workspace/persistence composition.

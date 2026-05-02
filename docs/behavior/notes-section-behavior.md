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
- Sidebar page entry: `frontend/src/app/chrome/sidebar/app-sidebar.tsx`

## Open notes view workflow

Entry paths:
1. Sidebar `Notes` button → `activeSection = "notes"`
2. `Alt+N` → same
3. Command palette "Pages" group → `Notes`

`activeSection === "notes"` → `SectionContent` renders `NotesSection` via `buildNotesSectionProps`.

## Saved note listing and filtering

### Notes section list

`NotesSection` renders one display-only card per `savedNotes` (most-recent-first). Each card shows: name, formatted save timestamp, shortened preview text. Empty state: `No saved notes available.`

### Sidebar filtering

Saved notes are no longer exposed in the sidebar command search while Playground-dependent note opening is retired.

## Open note

Opening saved notes into Playground is retired. Notes cards are display-only and do not navigate.

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
- Saved-note opening is retired; Notes cards do not change `activeSection`.
- App body renders section from `activeSection` only

### Active note

- `setActiveNoteId(note.id)` on save, new-note, open, duplicate resolution
- `activeSavedNote` derived from (`savedNotes`, `activeNoteId`)
- Autosave runs only when `activeNoteId` + `activeNoteName` both present; otherwise status `off`

### Breadcrumb/title

`AppBreadcrumb`: Notes section → title `Notes`.

## Behavioral test coverage

`frontend/src/test/app/` — save/open/autosave/sidebar search integration tests exercising `use-app-controller` + workspace/persistence composition.

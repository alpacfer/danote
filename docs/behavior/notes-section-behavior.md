# Notes section behavior

The Notes section is retired and hidden.

## Current user-facing behavior

- Sidebar navigation does not render a `Notes` button.
- `Alt+N` does not navigate to Notes.
- Command-palette page results exclude Notes.
- `SectionContent` cannot render `NotesSection` because `AppSection` no longer includes `"notes"`.
- Saved notes in local storage are not displayed in the app shell.

## Dormant code

The old Notes component, notes editor, and persistence helpers remain in the tree for now so existing local data is not destroyed by this UI change. They are not wired into app navigation.

## Coverage

`frontend/src/test/app/app-notes.test.tsx` asserts saved notes are not exposed in the current shell.

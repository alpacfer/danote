import { type ComponentProps } from "react"

import { NotesSection } from "@/app/sections/notes-section"

export type NotesSectionAdapterArgs = {
  savedNotes: ComponentProps<typeof NotesSection>["savedNotes"]
  openSavedNoteInPlayground: ComponentProps<typeof NotesSection>["onOpenSavedNote"]
}

export function buildNotesSectionProps({
  savedNotes,
  openSavedNoteInPlayground,
}: NotesSectionAdapterArgs): ComponentProps<typeof NotesSection> {
  return {
    savedNotes,
    onOpenSavedNote: openSavedNoteInPlayground,
  }
}

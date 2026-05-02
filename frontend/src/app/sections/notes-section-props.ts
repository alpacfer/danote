import { type ComponentProps } from "react"

import { NotesSection } from "@/app/sections/notes-section"

export type NotesSectionAdapterArgs = {
  savedNotes: ComponentProps<typeof NotesSection>["savedNotes"]
}

export function buildNotesSectionProps({
  savedNotes,
}: NotesSectionAdapterArgs): ComponentProps<typeof NotesSection> {
  return {
    savedNotes,
  }
}

import { Card, CardTitle } from "@/components/ui/card"
import {
  formatSavedNoteTimestamp,
  previewText,
  type SavedNote,
} from "@/app/core"

export type NotesSectionProps = {
  savedNotes: SavedNote[]
}

export function NotesSection({ savedNotes }: NotesSectionProps) {
  if (savedNotes.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved notes available.</p>
  }

  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {savedNotes.map((note) => {
        return (
          <Card key={note.id} className="p-0">
            <div className="w-full rounded-xl p-4 text-left">
              <div className="mb-2 flex items-center justify-between gap-3">
                <CardTitle className="text-base leading-tight">{note.name}</CardTitle>
                <p className="text-muted-foreground text-xs">{formatSavedNoteTimestamp(note.savedAt)}</p>
              </div>
              <p className="text-muted-foreground text-sm leading-relaxed">{previewText(note.text)}</p>
            </div>
          </Card>
        )
      })}
    </div>
  )
}

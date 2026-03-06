import type { PlaygroundSectionProps } from "@/app/sections/playground/playground-section-types"
import { PlaygroundHighlightPopover } from "@/app/sections/playground/playground-highlight-popover"
import { PlaygroundPhrasePopover } from "@/app/sections/playground/playground-phrase-popover"
import { PlaygroundSaveDialog } from "@/app/sections/playground/playground-save-dialog"
import { NotesEditor } from "@/components/notes-editor"

export type { PlaygroundSectionProps } from "@/app/sections/playground/playground-section-types"

export function PlaygroundSection(props: PlaygroundSectionProps) {
  const {
    noteText,
    noteHighlights,
    onNoteTextChange,
    onHighlightClick,
    onTextSelectionSettled,
    analysisError,
  } = props

  return (
    <div className="space-y-4">
      <PlaygroundSaveDialog {...props} />
      <div className="relative">
        <PlaygroundPhrasePopover {...props} />
        <PlaygroundHighlightPopover {...props} />
        <NotesEditor
          id="lesson-notes"
          placeholder="Type lesson notes here..."
          value={noteText}
          highlights={noteHighlights}
          onChange={onNoteTextChange}
          onHighlightClick={onHighlightClick}
          onTextSelectionSettled={onTextSelectionSettled}
        />
        <p className="text-muted-foreground absolute right-3 bottom-2 text-xs" aria-label="note-character-count">
          {noteText.length}
        </p>
      </div>
      {analysisError ? (
        <p className="text-destructive mt-2 text-sm" role="alert">
          {analysisError}
        </p>
      ) : null}
    </div>
  )
}

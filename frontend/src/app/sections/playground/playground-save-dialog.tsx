import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

import type { PlaygroundSectionProps } from "@/app/sections/playground/playground-section-types"

type PlaygroundSaveDialogProps = Pick<
  PlaygroundSectionProps,
  | "isSaveDialogOpen"
  | "saveDialogMode"
  | "noteNameDraft"
  | "duplicateNameConflictNoteId"
  | "onSaveDialogOpenChange"
  | "onNoteNameDraftChange"
  | "onSaveDialogSubmit"
  | "onResolveDuplicateName"
>

export function PlaygroundSaveDialog({
  isSaveDialogOpen,
  saveDialogMode,
  noteNameDraft,
  duplicateNameConflictNoteId,
  onSaveDialogOpenChange,
  onNoteNameDraftChange,
  onSaveDialogSubmit,
  onResolveDuplicateName,
}: PlaygroundSaveDialogProps) {
  return (
    <Dialog open={isSaveDialogOpen} onOpenChange={onSaveDialogOpenChange}>
      <DialogContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            onSaveDialogSubmit()
          }}
        >
          <DialogHeader>
            <DialogTitle>{saveDialogMode === "create_new" ? "Create new note" : "Save note"}</DialogTitle>
            {saveDialogMode === "create_new" ? (
              <DialogDescription>
                The current note will be saved. Creating a new note clears the editor.
              </DialogDescription>
            ) : (
              <DialogDescription>Name this note to store text and analysis.</DialogDescription>
            )}
          </DialogHeader>
          {saveDialogMode === "create_new" ? (
            <div className="space-y-2">
              <Label htmlFor="save-note-name-new">New note name</Label>
              <Input
                id="save-note-name-new"
                value={noteNameDraft}
                onChange={(event) => {
                  onNoteNameDraftChange(event.target.value)
                }}
                placeholder="My Danish note copy"
                autoComplete="off"
                autoFocus
              />
            </div>
          ) : (
            <div className="space-y-2">
              <Label htmlFor="save-note-name">Note name</Label>
              <Input
                id="save-note-name"
                value={noteNameDraft}
                onChange={(event) => {
                  onNoteNameDraftChange(event.target.value)
                }}
                placeholder="My Danish note"
                autoComplete="off"
                autoFocus
              />
            </div>
          )}
          {duplicateNameConflictNoteId ? (
            <p className="text-muted-foreground text-sm">
              {saveDialogMode === "create_new"
                ? "A note with this title already exists. Use it or change the name."
                : "A note with this title already exists. Overwrite it or change the name."}
            </p>
          ) : null}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onSaveDialogOpenChange(false)}>
              Cancel
            </Button>
            {duplicateNameConflictNoteId ? (
              <Button type="button" onClick={onResolveDuplicateName}>
                {saveDialogMode === "create_new" ? "Use existing note" : "Overwrite existing"}
              </Button>
            ) : null}
            {saveDialogMode === "create_new" ? <Button type="submit">Create new note</Button> : <Button type="submit">Save</Button>}
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

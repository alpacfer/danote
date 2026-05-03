import { RotateCcw, Save } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export type GeneratedExamplePreview = {
  source_text: string
  english_translation: string
  target: { stored_lemma: string; meaning_id: number }
}

type GeneratedExampleDialogProps = {
  preview: GeneratedExamplePreview | null
  isSaving: boolean
  isRegenerating: boolean
  onSave: () => void
  onRegenerate: () => void
  onDiscard: () => void
}

export function GeneratedExampleDialog({
  preview,
  isSaving,
  isRegenerating,
  onSave,
  onRegenerate,
  onDiscard,
}: GeneratedExampleDialogProps) {
  const isBusy = isSaving || isRegenerating
  return (
    <Dialog
      open={preview !== null}
      onOpenChange={(open) => {
        if (!open && !isBusy) {
          onDiscard()
        }
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Generated example</DialogTitle>
          <DialogDescription>Review this example before saving it to sentencebank.</DialogDescription>
        </DialogHeader>
        {preview ? (
          <div className="space-y-2">
            <p className="text-base font-medium leading-relaxed break-words">{preview.source_text}</p>
            <p className="text-muted-foreground text-sm leading-relaxed break-words">
              {preview.english_translation}
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onDiscard} disabled={isBusy}>
            Discard
          </Button>
          <Button type="button" variant="outline" onClick={onRegenerate} disabled={isBusy}>
            <RotateCcw className={`size-4 ${isRegenerating ? "animate-spin" : ""}`.trim()} />
            {isRegenerating ? "Regenerating..." : "Regenerate"}
          </Button>
          <Button type="button" onClick={onSave} disabled={isBusy}>
            <Save className="size-4" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

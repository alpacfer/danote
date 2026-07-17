import { RotateCcw, Save } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
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
  target:
    | { kind: "wordbank"; stored_lemma: string; meaning_id: number }
    | { kind: "static"; stored_lemma: string }
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
          <Card className="danote-example-clipping py-4" data-material="sentence">
            <CardContent className="flex flex-col gap-2 px-4">
            <p className="text-base font-medium leading-relaxed break-words">{preview.source_text}</p>
            <p className="text-muted-foreground text-sm leading-relaxed break-words">
              {preview.english_translation}
            </p>
            </CardContent>
          </Card>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onDiscard} disabled={isBusy}>
            Discard
          </Button>
          <Button type="button" variant="outline" onClick={onRegenerate} disabled={isBusy}>
            <RotateCcw data-icon="inline-start" className={isRegenerating ? "animate-spin" : undefined} />
            {isRegenerating ? "Regenerating..." : "Regenerate"}
          </Button>
          <Button type="button" onClick={onSave} disabled={isBusy}>
            <Save data-icon="inline-start" />
            {isSaving ? "Saving..." : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

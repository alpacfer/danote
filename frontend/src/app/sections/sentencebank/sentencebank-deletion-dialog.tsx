import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export function SentenceDeletionDialog({
  sentence,
  onOpenChange,
  onConfirm,
}: {
  sentence: SentencebankSentence | null
  onOpenChange: (open: boolean) => void
  onConfirm: (deleteMeanings: boolean) => void
}) {
  const translation = sentence
    ? formatSentenceTranslation(sentence.english_translation) || "No translation available."
    : ""

  return (
    <Dialog open={sentence !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete sentence</DialogTitle>
          <DialogDescription>
            Choose whether to keep the word bank meanings linked from this sentence.
          </DialogDescription>
        </DialogHeader>
        {sentence ? (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="font-medium">{sentence.source_text}</p>
            <p className="text-muted-foreground text-sm">{translation}</p>
          </div>
        ) : null}
        <DialogFooter className="sm:justify-between">
          <DialogClose asChild>
            <Button type="button" variant="outline">Cancel</Button>
          </DialogClose>
          <div className="flex flex-col-reverse gap-2 sm:flex-row">
            <Button type="button" variant="outline" onClick={() => onConfirm(false)}>
              Just delete the sentence
            </Button>
            <Button type="button" variant="destructive" onClick={() => onConfirm(true)}>
              Delete sentence and meanings
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

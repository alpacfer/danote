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

export type MeaningDeleteTarget = {
  id: number
  label: string
  translation: string | null
}

export function MeaningDeletionDialog({
  meaning,
  onOpenChange,
  onConfirm,
}: {
  meaning: MeaningDeleteTarget | null
  onOpenChange: (open: boolean) => void
  onConfirm: (meaningId: number) => void
}) {
  return (
    <Dialog open={meaning !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete meaning</DialogTitle>
          <DialogDescription>
            This removes the saved meaning from your word bank. Sentence tokens that used it will stay in their sentences and become unsaved.
          </DialogDescription>
        </DialogHeader>
        {meaning ? (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="font-medium">{meaning.label}</p>
            {meaning.translation ? (
              <p className="text-muted-foreground text-sm italic">{meaning.translation}</p>
            ) : null}
          </div>
        ) : null}
        <p className="text-muted-foreground text-sm">
          If this is the last saved meaning for the lemma, the whole lemma page will be deleted.
        </p>
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            type="button"
            variant="destructive"
            onClick={() => {
              if (meaning) onConfirm(meaning.id)
            }}
          >
            Delete meaning
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export function LemmaDeletionDialog({
  lemma,
  onOpenChange,
  onConfirm,
}: {
  lemma: { lemma: string; displayWord: string } | null
  onOpenChange: (open: boolean) => void
  onConfirm: (lemma: string) => void
}) {
  return (
    <Dialog open={lemma !== null} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete whole lemma</DialogTitle>
          <DialogDescription>
            This permanently removes the lemma and all of its saved meanings from your word bank.
          </DialogDescription>
        </DialogHeader>
        {lemma ? (
          <div className="rounded-md border bg-muted/30 p-3">
            <p className="font-medium">{lemma.displayWord}</p>
            <p className="text-muted-foreground text-sm">
              Sentence tokens that used this lemma will stay in place and become unsaved.
            </p>
          </div>
        ) : null}
        <DialogFooter>
          <DialogClose asChild>
            <Button type="button" variant="outline">Cancel</Button>
          </DialogClose>
          <Button
            type="button"
            variant="destructive"
            onClick={() => {
              if (lemma) onConfirm(lemma.lemma)
            }}
          >
            Delete lemma
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

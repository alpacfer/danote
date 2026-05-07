import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { SentenceHighlightedText } from "@/app/components/sentence-highlighted-text"
import { matchedTokenIndexes } from "@/app/sections/wordbank/_shared/pinned-page-token-matchers"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"

type PinnedExamplesDialogProps = {
  lemma: string
  open: boolean
  onOpenChange: (open: boolean) => void
  sentences: SentencebankSentence[]
  onOpenSentence?: (id: number) => void
}

export function PinnedExamplesDialog({
  lemma,
  open,
  onOpenChange,
  sentences,
  onOpenSentence,
}: PinnedExamplesDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[min(720px,calc(100vh-2rem))] grid-rows-[auto_minmax(0,1fr)] sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>{lemma} examples</DialogTitle>
          <DialogDescription className="sr-only">
            Saved example sentences containing this word.
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="min-h-0 pr-3">
          <div className="space-y-2">
            {sentences.map((sentence) => (
              <button
                key={sentence.id}
                type="button"
                className="hover:bg-accent/50 w-full rounded-md border p-3 text-left transition-colors"
                onClick={() => {
                  onOpenChange(false)
                  onOpenSentence?.(sentence.id)
                }}
                disabled={!onOpenSentence}
              >
                <p className="text-sm font-medium leading-relaxed break-words">
                  <SentenceHighlightedText
                    sourceText={sentence.source_text}
                    tokens={sentence.tokens}
                    highlightedTokenIndexes={matchedTokenIndexes(lemma, sentence)}
                  />
                </p>
                <p className="text-muted-foreground mt-1 text-xs break-words">
                  {formatSentenceTranslation(sentence.english_translation) || "No translation available."}
                </p>
              </button>
            ))}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  )
}


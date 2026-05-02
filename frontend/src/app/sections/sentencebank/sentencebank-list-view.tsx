import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

type SentencebankListViewProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  onOpenSentence: (id: number) => void
}

export function SentencebankListView({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  onOpenSentence,
}: SentencebankListViewProps) {
  if (sentencebankError) {
    return (
      <p className="text-destructive text-sm" role="alert">
        {sentencebankError}
      </p>
    )
  }

  if (isSentencebankLoading && sentences.length === 0) {
    return (
      <div className="space-y-3">
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-32" />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="space-y-2">
            <Skeleton className="h-5 w-56" />
            <Skeleton className="h-4 w-36" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (sentences.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved sentences yet.</p>
  }

  return (
    <ScrollArea className="min-h-0 flex-1">
      <div className="space-y-3 pr-1">
        {sentences.map((sentence) => (
          <button
            key={sentence.id}
            type="button"
            className="w-full text-left"
            onClick={() => onOpenSentence(sentence.id)}
          >
            <Card className="hover:bg-accent/40 transition-colors cursor-pointer">
              <CardContent className="space-y-2">
                <p className="text-base font-medium leading-relaxed max-w-[70ch] break-words">{sentence.source_text}</p>
                <p className="text-muted-foreground text-sm max-w-[70ch] break-words">
                  {formatSentenceTranslation(sentence.english_translation) || "No translation available."}
                </p>
              </CardContent>
            </Card>
          </button>
        ))}
      </div>
    </ScrollArea>
  )
}

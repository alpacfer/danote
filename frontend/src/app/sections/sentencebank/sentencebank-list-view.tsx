import { useEffect, useRef, useState } from "react"

import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

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
      <div className="flex flex-wrap gap-3 items-start pr-1">
        {sentences.map((sentence) => (
          <SentenceCard
            key={sentence.id}
            sentence={sentence}
            onOpen={() => onOpenSentence(sentence.id)}
          />
        ))}
      </div>
    </ScrollArea>
  )
}

type SentenceCardProps = {
  sentence: SentencebankSentence
  onOpen: () => void
}

function SentenceCard({ sentence, onOpen }: SentenceCardProps) {
  const sourceRef = useRef<HTMLParagraphElement>(null)
  const translationRef = useRef<HTMLParagraphElement>(null)
  const [isTruncated, setIsTruncated] = useState(false)

  useEffect(() => {
    const check = () => {
      const src = sourceRef.current
      const trl = translationRef.current
      setIsTruncated(
        (src != null && src.scrollWidth > src.offsetWidth) ||
        (trl != null && trl.scrollWidth > trl.offsetWidth),
      )
    }
    check()
    const observer = new ResizeObserver(check)
    if (sourceRef.current) observer.observe(sourceRef.current)
    if (translationRef.current) observer.observe(translationRef.current)
    return () => observer.disconnect()
  }, [sentence.source_text, sentence.english_translation])

  const translation = formatSentenceTranslation(sentence.english_translation) || "No translation available."

  return (
    <Tooltip open={isTruncated ? undefined : false}>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="text-left"
          onClick={onOpen}
        >
          <Card className="hover:bg-accent/40 transition-colors cursor-pointer max-w-sm">
            <CardContent className="space-y-1.5">
              <p ref={sourceRef} className="text-base font-medium leading-snug truncate">{sentence.source_text}</p>
              <p ref={translationRef} className="text-muted-foreground text-sm truncate">{translation}</p>
            </CardContent>
          </Card>
        </button>
      </TooltipTrigger>
      <TooltipContent side="bottom" className="max-w-xs">
        <p className="font-medium">{sentence.source_text}</p>
        <p className="text-muted-foreground mt-0.5">{translation}</p>
      </TooltipContent>
    </Tooltip>
  )
}

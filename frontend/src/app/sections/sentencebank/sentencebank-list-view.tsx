import { useEffect, useRef, useState } from "react"

import { formatSentenceTranslation, type SentencebankSentence } from "@/app/core"
import { SentenceDeletionDialog } from "@/app/sections/sentencebank/sentencebank-deletion-dialog"
import { Card, CardContent } from "@/components/ui/card"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import { Trash2 } from "lucide-react"

type SentencebankListViewProps = {
  sentencebankError: string | null
  isSentencebankLoading: boolean
  sentences: SentencebankSentence[]
  onOpenSentence: (id: number) => void
  onDeleteSentence: (id: number, deleteMeanings: boolean) => void
}

export function SentencebankListView({
  sentencebankError,
  isSentencebankLoading,
  sentences,
  onOpenSentence,
  onDeleteSentence,
}: SentencebankListViewProps) {
  const [sentenceToDelete, setSentenceToDelete] = useState<SentencebankSentence | null>(null)

  const title = (
    <h1 className="font-section-title flex h-8 items-center text-2xl leading-none font-normal tracking-normal" data-grid-anchor="rule">
      Sentences
    </h1>
  )

  if (sentencebankError) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4" data-grid-page="sentencebank-list">
        {title}
        <p className="text-destructive text-sm" role="alert">
          {sentencebankError}
        </p>
      </div>
    )
  }

  if (isSentencebankLoading && sentences.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4" data-grid-page="sentencebank-list">
        {title}
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
      </div>
    )
  }

  if (sentences.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 flex-col gap-4" data-grid-page="sentencebank-list">
        {title}
        <p className="text-muted-foreground text-sm">No saved sentences yet.</p>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4" data-grid-page="sentencebank-list">
      {title}
      <div className="flex flex-wrap items-start gap-4" data-grid-anchor="unit">
        {sentences.map((sentence) => (
          <SentenceCard
            key={sentence.id}
            sentence={sentence}
            onOpen={() => onOpenSentence(sentence.id)}
            onRequestDelete={() => setSentenceToDelete(sentence)}
          />
        ))}
      </div>
      <SentenceDeletionDialog
        sentence={sentenceToDelete}
        onOpenChange={(open) => {
          if (!open) setSentenceToDelete(null)
        }}
        onConfirm={(deleteMeanings) => {
          if (!sentenceToDelete) return
          onDeleteSentence(sentenceToDelete.id, deleteMeanings)
          setSentenceToDelete(null)
        }}
      />
    </div>
  )
}

type SentenceCardProps = {
  sentence: SentencebankSentence
  onOpen: () => void
  onRequestDelete: () => void
}

function SentenceCard({ sentence, onOpen, onRequestDelete }: SentenceCardProps) {
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
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div>
          <Tooltip open={isTruncated ? undefined : false}>
            <TooltipTrigger asChild>
              <button
                type="button"
                className="text-left"
                onClick={onOpen}
              >
                <Card
                  className="hover:bg-accent/40 max-w-sm cursor-pointer transition-colors"
                  data-material="sentence"
                  data-grid-anchor="unit"
                >
                  <CardContent className="space-y-1.5">
                    <p ref={sourceRef} className="font-lexical truncate text-lg leading-snug font-semibold tracking-[-0.01em]">
                      {sentence.source_text}
                    </p>
                    <p ref={translationRef} className="text-muted-foreground text-sm truncate">{translation}</p>
                  </CardContent>
                </Card>
              </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" className="max-w-xs">
              <p className="font-lexical text-base font-semibold tracking-[-0.01em]">{sentence.source_text}</p>
              <p className="text-muted-foreground mt-0.5">{translation}</p>
            </TooltipContent>
          </Tooltip>
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem variant="destructive" onSelect={onRequestDelete}>
          <Trash2 />
          Delete sentence
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

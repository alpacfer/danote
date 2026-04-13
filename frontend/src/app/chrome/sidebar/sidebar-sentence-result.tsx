import { Languages, Loader2, Plus } from "lucide-react"

import { formatSentenceTranslation, type SentenceSearchPreviewResponse } from "@/app/core"
import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"

type SidebarSentenceResultProps = {
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceSearchPreviewLoading: boolean
  onSaveSentence: (sourceText: string, englishTranslation: string | null) => Promise<void>
}

export function SidebarSentenceResult({
  sentenceSearchPreview,
  isSentenceSearchPreviewLoading,
  onSaveSentence,
}: SidebarSentenceResultProps) {
  const isBlocked = sentenceSearchPreview?.status === "blocked"
  const isSaveDisabled = isSentenceSearchPreviewLoading
    || sentenceSearchPreview === null
    || sentenceSearchPreview.source_text === null
    || isBlocked
  const displayText = sentenceSearchPreview?.source_text?.trim() ?? null
  const displayTranslation = formatSentenceTranslation(sentenceSearchPreview?.english_translation)
  const isEnglishQuery = sentenceSearchPreview?.query_language === "en"
  const secondaryText = sentenceSearchPreview?.message
    ? sentenceSearchPreview.message
    : (displayTranslation ?? null)

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          if (isSaveDisabled) return
          void onSaveSentence(
            sentenceSearchPreview.source_text,
            sentenceSearchPreview.english_translation,
          )
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-0.5">
          {displayText ? (
            <p className="line-clamp-2 text-sm font-semibold break-words">{displayText}</p>
          ) : null}
          {isSentenceSearchPreviewLoading ? (
            <Skeleton
              className="h-3 w-24 bg-accent group-data-[selected=true]/search-item:bg-accent-foreground/20"
              data-testid="sentence-search-translation-skeleton"
            />
          ) : secondaryText ? (
            <span className="text-muted-foreground text-xs leading-4 break-words flex items-center gap-1">
              {isEnglishQuery ? <Languages className="size-3 shrink-0" aria-label="Translated from English" /> : null}
              {secondaryText}
            </span>
          ) : null}
        </div>
        {isSentenceSearchPreviewLoading ? (
          <Loader2 className="text-muted-foreground size-4 shrink-0 animate-spin" />
        ) : (
          <Plus
            className={
              isSaveDisabled
                ? "text-muted-foreground/40 size-4 shrink-0"
                : "text-muted-foreground size-4 shrink-0"
            }
          />
        )}
      </CommandItem>
    </CommandGroup>
  )
}

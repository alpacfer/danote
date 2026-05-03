import { Loader2, Plus } from "lucide-react"

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
  const secondaryText = sentenceSearchPreview?.message
    ? sentenceSearchPreview.message
    : (displayTranslation ?? null)

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          const preview = sentenceSearchPreview
          if (isSaveDisabled || preview === null || preview.source_text === null) return
          void onSaveSentence(preview.source_text, preview.english_translation)
        }}
        className="flex items-center gap-6 pr-6!"
      >
        <div className="flex min-w-0 flex-1 flex-col items-start gap-0.5">
          {displayText ? (
            <span className="flex items-center gap-1">
              <p className="line-clamp-2 text-sm font-semibold break-words">{displayText}</p>
            </span>
          ) : isSentenceSearchPreviewLoading ? (
            <Skeleton
              className="h-5 w-40 bg-accent group-data-[selected=true]/search-item:bg-accent-foreground/20"
              data-testid="sentence-search-text-skeleton"
            />
          ) : null}
          {secondaryText ? (
            <span className="text-muted-foreground text-xs leading-4 break-words">
              {secondaryText}
            </span>
          ) : isSentenceSearchPreviewLoading ? (
            <Skeleton
              className="h-4 w-24 bg-accent group-data-[selected=true]/search-item:bg-accent-foreground/20"
              data-testid="sentence-search-translation-skeleton"
            />
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

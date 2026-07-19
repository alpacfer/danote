import { Loader2 } from "lucide-react"

import {
  SearchResultAction,
  SearchSection,
} from "@/app/chrome/sidebar/sidebar-search-presentation"
import { formatSentenceTranslation, type SentenceSearchPreviewResponse } from "@/app/core"
import { CommandItem } from "@/components/ui/command"
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
    <SearchSection heading="Sentence to save" material="sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        data-search-slip
        data-material="sentence"
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
              <p data-search-lexical className="line-clamp-2 font-semibold break-words">
                {displayText}
              </p>
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
          <span data-search-result-action className="text-muted-foreground">
            <span>Checking</span>
            <Loader2 className="animate-spin" aria-hidden />
          </span>
        ) : (
          <SearchResultAction kind="add" muted={isSaveDisabled} />
        )}
      </CommandItem>
    </SearchSection>
  )
}

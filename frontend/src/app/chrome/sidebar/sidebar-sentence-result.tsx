import { Loader2, Plus } from "lucide-react"

import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import { type SentenceVerificationErrorItem, type VerifySentenceResponse } from "@/app/core/types-api"

type TextSegment = { text: string; isError: boolean }

function buildSegments(text: string, errors: SentenceVerificationErrorItem[]): TextSegment[] {
  if (!errors.length) return [{ text, isError: false }]

  const sorted = [...errors].sort((a, b) => a.start - b.start)
  const segments: TextSegment[] = []
  let cursor = 0

  for (const err of sorted) {
    if (err.start > cursor) {
      segments.push({ text: text.slice(cursor, err.start), isError: false })
    }
    segments.push({ text: text.slice(err.start, err.end), isError: true })
    cursor = err.end
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), isError: false })
  }

  return segments
}

type SidebarSentenceResultProps = {
  sourceText: string
  englishTranslation: string | null
  isTranslationLoading: boolean
  sentenceVerification: VerifySentenceResponse | null
  isSentenceVerificationLoading: boolean
  onSaveSentence: (sourceText: string) => Promise<void>
  onCloseSearch: () => void
}

export function SidebarSentenceResult({
  sourceText,
  englishTranslation,
  isTranslationLoading,
  sentenceVerification,
  isSentenceVerificationLoading,
  onSaveSentence,
  onCloseSearch,
}: SidebarSentenceResultProps) {
  const isSaveDisabled = isSentenceVerificationLoading || sentenceVerification === null
  const textToSave = sentenceVerification?.corrected_text ?? sourceText

  const hasErrors = sentenceVerification !== null && !sentenceVerification.is_valid
  const segments = hasErrors
    ? buildSegments(sourceText, sentenceVerification.errors)
    : null

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          if (isSaveDisabled) return
          void (async () => {
            await onSaveSentence(textToSave)
            onCloseSearch()
          })()
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-1">
          <span className="text-sm font-semibold break-words">
            {segments
              ? segments.map((seg, i) =>
                  seg.isError ? (
                    <span key={i} className="underline decoration-red-500 decoration-wavy">
                      {seg.text}
                    </span>
                  ) : (
                    <span key={i}>{seg.text}</span>
                  ),
                )
              : sourceText}
          </span>
          {isTranslationLoading ? (
            <Skeleton className="h-4 w-28" data-testid="sentence-search-translation-skeleton" />
          ) : (
            <span className="text-muted-foreground text-xs leading-4 break-words">
              {englishTranslation?.trim() || "No translation available."}
            </span>
          )}
          {hasErrors && sentenceVerification.corrected_text ? (
            <p className="text-xs text-muted-foreground mt-1">
              <span className="font-medium">Corrected: </span>
              {sentenceVerification.corrected_text}
            </p>
          ) : null}
        </div>
        {isSentenceVerificationLoading ? (
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

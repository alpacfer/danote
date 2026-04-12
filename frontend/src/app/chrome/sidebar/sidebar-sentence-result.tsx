import { Loader2, Plus } from "lucide-react"

import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import { type VerifySentenceResponse } from "@/app/core/types-api"

type SidebarSentenceResultProps = {
  sourceText: string
  englishTranslation: string | null
  isTranslationLoading: boolean
  sentenceVerification: VerifySentenceResponse | null
  isSentenceVerificationLoading: boolean
  onSaveSentence: (sourceText: string, englishTranslation: string | null) => Promise<void>
}

export function SidebarSentenceResult({
  sourceText,
  englishTranslation,
  isTranslationLoading,
  sentenceVerification,
  isSentenceVerificationLoading,
  onSaveSentence,
}: SidebarSentenceResultProps) {
  const isSaveDisabled = isSentenceVerificationLoading || sentenceVerification === null
  const textToSave = sentenceVerification?.corrected_text ?? sourceText
  const displayText = textToSave.trim() || sourceText

  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        disabled={isSaveDisabled}
        onSelect={() => {
          if (isSaveDisabled) return
          void onSaveSentence(textToSave, englishTranslation)
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-1">
          <p className="text-sm font-semibold break-words">{displayText}</p>
          {isTranslationLoading ? (
            <Skeleton className="h-4 w-28" data-testid="sentence-search-translation-skeleton" />
          ) : (
            <span className="text-muted-foreground text-xs leading-4 break-words">
              {englishTranslation?.trim() || "No translation available."}
            </span>
          )}
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

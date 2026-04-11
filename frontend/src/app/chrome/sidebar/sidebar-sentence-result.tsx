import { Plus } from "lucide-react"

import { CommandGroup, CommandItem } from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"

type SidebarSentenceResultProps = {
  sourceText: string
  englishTranslation: string | null
  isTranslationLoading: boolean
  onSaveSentence: (sourceText: string) => Promise<void>
  onCloseSearch: () => void
}

export function SidebarSentenceResult({
  sourceText,
  englishTranslation,
  isTranslationLoading,
  onSaveSentence,
  onCloseSearch,
}: SidebarSentenceResultProps) {
  return (
    <CommandGroup heading="Sentence">
      <CommandItem
        value="sentence-translation-result"
        onSelect={() => {
          void (async () => {
            await onSaveSentence(sourceText)
            onCloseSearch()
          })()
        }}
        className="flex items-center justify-between gap-3"
      >
        <div className="flex min-w-0 flex-col items-start gap-1">
          <span className="text-sm font-semibold break-words">{sourceText}</span>
          {isTranslationLoading ? (
            <Skeleton className="h-4 w-28" data-testid="sentence-search-translation-skeleton" />
          ) : (
            <span className="text-muted-foreground text-xs leading-4 break-words">
              {englishTranslation?.trim() || "No translation available."}
            </span>
          )}
        </div>
        <Plus className="text-muted-foreground size-4 shrink-0" />
      </CommandItem>
    </CommandGroup>
  )
}

import { useState } from "react"

import { LemmaDeletionDialog } from "@/app/sections/wordbank/wordbank-deletion-dialogs"
import { PINNED_PAGES } from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import { WordbankListFilters, type WordbankFilterState } from "@/app/sections/wordbank/wordbank-list-filters"
import { WordbankListResults, PinnedGroupSection } from "@/app/sections/wordbank/wordbank-list-results"
import type { WordbankSectionProps } from "@/app/sections/wordbank/wordbank-section-types"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"

type WordbankListViewProps = Pick<
  WordbankSectionProps,
  "wordbankError" | "isWordbankLoading" | "lemmas" | "unreadWordbankLemmaCounts" | "onSelectLemma"
  | "onDeleteLemma"
> & {
  filters: WordbankFilterState
  onFiltersChange: (filters: WordbankFilterState) => void
}

export function WordbankListView({
  wordbankError,
  isWordbankLoading,
  lemmas,
  unreadWordbankLemmaCounts,
  onSelectLemma,
  onDeleteLemma,
  filters,
  onFiltersChange,
}: WordbankListViewProps) {
  const [lemmaToDelete, setLemmaToDelete] = useState<{ lemma: string; displayWord: string } | null>(null)

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <h1 className="font-section-title text-2xl leading-none font-normal tracking-normal">Words</h1>
      {wordbankError ? (
        <p className="text-destructive text-sm" role="alert">
          {wordbankError}
        </p>
      ) : null}
      {isWordbankLoading && lemmas.length === 0 ? (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-16 rounded-md" />
              <Skeleton className="h-8 w-20 rounded-md" />
              <Skeleton className="h-8 w-14 rounded-md" />
              <Skeleton className="h-8 w-24 rounded-md" />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-[4.5rem] rounded-md" />
              <Skeleton className="h-8 w-12 rounded-md" />
              <Skeleton className="h-8 w-[5.5rem] rounded-md" />
            </div>
          </div>
          <div className="flex flex-col gap-2">
            <Skeleton className="h-3 w-4" />
            <div className="flex flex-wrap gap-2">
              <Skeleton className="h-8 w-[3.75rem] rounded-md" />
              <Skeleton className="h-8 w-[4.75rem] rounded-md" />
              <Skeleton className="h-8 w-[2.75rem] rounded-md" />
              <Skeleton className="h-8 w-[4.25rem] rounded-md" />
            </div>
          </div>
        </div>
      ) : (
        <>
          <PinnedGroupSection pages={PINNED_PAGES} onSelectLemma={onSelectLemma} />
          <WordbankListFilters lemmas={lemmas} filters={filters} onFiltersChange={onFiltersChange} />
          <ScrollArea className="min-h-0 flex-1">
            <WordbankListResults
              lemmas={lemmas}
              filters={filters}
              unreadWordbankLemmaCounts={unreadWordbankLemmaCounts}
              onSelectLemma={onSelectLemma}
              onRequestDelete={setLemmaToDelete}
              onClearFilters={() => onFiltersChange({ posTags: [], categories: [] })}
            />
          </ScrollArea>
        </>
      )}
      <LemmaDeletionDialog
        lemma={lemmaToDelete}
        onOpenChange={(open) => {
          if (!open) setLemmaToDelete(null)
        }}
        onConfirm={(lemma) => {
          onDeleteLemma(lemma)
          setLemmaToDelete(null)
        }}
      />
    </div>
  )
}

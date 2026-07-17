import { FilterX } from "lucide-react"

import { isMultiWordLemma, type WordbankLemma } from "@/app/core"
import type { WordbankFilterState } from "@/app/sections/wordbank/wordbank-list-filters"
import { WordbankSpecimenTile } from "@/app/sections/wordbank/wordbank-specimen-tile"
import { Button } from "@/components/ui/button"
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from "@/components/ui/empty"

type WordbankListResultsProps = {
  lemmas: WordbankLemma[]
  filters: WordbankFilterState
  unreadWordbankLemmaCounts: Map<string, number>
  onSelectLemma: (lemma: string) => void
  onRequestDelete: (lemma: { lemma: string; displayWord: string }) => void
  onClearFilters: () => void
}

export function WordbankListResults({
  lemmas,
  filters,
  unreadWordbankLemmaCounts,
  onSelectLemma,
  onRequestDelete,
  onClearFilters,
}: WordbankListResultsProps) {
  const filteredGroups = groupWordbankLemmas(filterLemmas(lemmas, filters))
  const hasActiveFilters = filters.posTags.length > 0 || filters.categories.length > 0

  return (
    <div className="flex flex-col gap-6" data-grid-anchor="unit">
      {hasActiveFilters && filteredGroups.length === 0 ? <WordbankListEmpty onClearFilters={onClearFilters} /> : null}

      {filteredGroups.map((group) => (
        <section key={group.letter} className="flex flex-col gap-2" data-grid-anchor="unit">
          <h3 className="text-muted-foreground flex h-8 items-center text-xs font-semibold tracking-wide uppercase">
            {group.letter}
          </h3>
          <div className="flex flex-wrap gap-2">
            {group.items.map((lemma) => {
              const displayWord = lemma.display_lemma?.trim() || lemma.lemma
              const unreadCount = unreadWordbankLemmaCounts.get(lemma.lemma) ?? 0
              return (
                <WordbankSpecimenTile
                  key={lemma.lemma}
                  lemma={lemma}
                  unreadCount={unreadCount}
                  onSelect={() => onSelectLemma(lemma.lemma)}
                  onRequestDelete={() => onRequestDelete({ lemma: lemma.lemma, displayWord })}
                />
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}

function WordbankListEmpty({ onClearFilters }: { onClearFilters: () => void }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <FilterX />
        </EmptyMedia>
        <EmptyTitle>No matching lemmas</EmptyTitle>
        <EmptyDescription>Clear filters to show the full wordbank again.</EmptyDescription>
      </EmptyHeader>
      <Button type="button" variant="outline" size="sm" onClick={onClearFilters}>
        Clear filters
      </Button>
    </Empty>
  )
}

function filterLemmas(lemmas: WordbankLemma[], filters: WordbankFilterState): WordbankLemma[] {
  return lemmas.filter((lemma) => {
    const lemmaPosTags = new Set((lemma.pos_tags ?? []).map((posTag) => posTag.trim().toUpperCase()).filter(Boolean))
    const lemmaCategories = new Set((lemma.categories ?? []).map((category) => category.trim()).filter(Boolean))
    const matchesPos = filters.posTags.length === 0 || filters.posTags.some((posTag) => {
      if (posTag === "PHRASAL_VERB") return isMultiWordLemma(lemma.lemma) && (lemma.pos_tags?.includes("VERB") || lemma.pos_tags?.includes("AUX"));
      if (posTag === "IDIOM") return isMultiWordLemma(lemma.lemma) && !(lemma.pos_tags?.includes("VERB") || lemma.pos_tags?.includes("AUX"));
      return lemmaPosTags.has(posTag);
    })
    const matchesCategories =
      filters.categories.length === 0 || filters.categories.every((category) => lemmaCategories.has(category))
    return matchesPos && matchesCategories
  })
}

function groupWordbankLemmas(lemmas: WordbankLemma[]) {
  const collator = new Intl.Collator("da", { sensitivity: "base" })
  const sortedLemmas = [...lemmas].sort((left, right) => collator.compare(left.lemma, right.lemma))
  const groups = new Map<string, WordbankLemma[]>()

  for (const lemma of sortedLemmas) {
    const normalizedLemma = lemma.lemma.trim()
    if (!normalizedLemma) continue
    const groupLetter = normalizedLemma[0].toLocaleUpperCase("da-DK")
    if (!groups.has(groupLetter)) {
      groups.set(groupLetter, [])
    }
    groups.get(groupLetter)?.push(lemma)
  }

  return Array.from(groups.entries())
    .sort(([left], [right]) => collator.compare(left, right))
    .map(([letter, items]) => ({ letter, items }))
}

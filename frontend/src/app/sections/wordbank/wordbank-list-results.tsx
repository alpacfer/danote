import { useRef, useState } from "react"
import { FilterX } from "lucide-react"

import { isMultiWordLemma, type WordbankLemma } from "@/app/core"
import {
  catalogueGroupId,
  useActiveCatalogueLetter,
} from "@/app/sections/wordbank/wordbank-alphabet"
import { WordbankAlphabetIndex } from "@/app/sections/wordbank/wordbank-alphabet-index"
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
  const catalogueRef = useRef<HTMLDivElement>(null)
  const [expandedLemma, setExpandedLemma] = useState<string | null>(null)
  const letters = filteredGroups.map((group) => group.letter)
  const availableLetters = new Set(letters)
  const [activeLetter, setActiveLetter] = useActiveCatalogueLetter(catalogueRef, letters)
  const hasActiveFilters = filters.posTags.length > 0 || filters.categories.length > 0

  function scrollToLetter(letter: string) {
    const group = document.getElementById(catalogueGroupId(letter))
    if (!group) return
    setActiveLetter(letter)
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (typeof group.scrollIntoView === "function") {
      group.scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" })
    }
  }

  return (
    <div
      ref={catalogueRef}
      className="grid min-w-0 grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_4rem]"
      data-grid-anchor="unit"
      data-wordbank-catalogue
    >
      {hasActiveFilters && filteredGroups.length === 0 ? (
        <div className="md:col-span-2">
          <WordbankListEmpty onClearFilters={onClearFilters} />
        </div>
      ) : null}

      {filteredGroups.length > 0 ? (
        <>
          <WordbankAlphabetIndex
            activeLetter={activeLetter}
            availableLetters={availableLetters}
            onSelectLetter={scrollToLetter}
          />
          <div className="flex min-w-0 flex-col gap-8 md:order-1">
            {filteredGroups.map((group) => (
              <section
                key={group.letter}
                id={catalogueGroupId(group.letter)}
                className="grid min-w-0 grid-cols-[2rem_minmax(0,1fr)] gap-2 sm:grid-cols-[3rem_minmax(0,1fr)] sm:gap-4"
                data-grid-anchor="unit"
                data-wordbank-letter={group.letter}
              >
                <h3 className="text-muted-foreground sticky top-12 flex h-8 items-center justify-start self-start md:top-4">
                  <span className="font-section-title text-2xl leading-none">{group.letter}</span>
                </h3>
                <div className="grid min-w-0 grid-cols-1 gap-2 min-[30rem]:grid-cols-2 lg:grid-cols-[repeat(auto-fill,minmax(10rem,1fr))]">
                  {group.items.map((lemma) => {
                    const displayWord = lemma.display_lemma?.trim() || lemma.lemma
                    const unreadCount = unreadWordbankLemmaCounts.get(lemma.lemma) ?? 0
                    return (
                      <WordbankSpecimenTile
                        key={lemma.lemma}
                        lemma={lemma}
                        unreadCount={unreadCount}
                        expanded={expandedLemma === lemma.lemma}
                        onExpandedChange={(open) => {
                          setExpandedLemma((current) => {
                            if (open) return lemma.lemma
                            return current === lemma.lemma ? null : current
                          })
                        }}
                        onSelect={() => onSelectLemma(lemma.lemma)}
                        onRequestDelete={() => onRequestDelete({ lemma: lemma.lemma, displayWord })}
                      />
                    )
                  })}
                </div>
              </section>
            ))}
          </div>
        </>
      ) : null}
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

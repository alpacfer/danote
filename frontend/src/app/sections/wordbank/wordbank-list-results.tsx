import { ChevronRight, FilterX, Trash2 } from "lucide-react"

import type { WordbankLemma } from "@/app/core"
import type { PinnedPageMeta } from "@/app/sections/wordbank/_shared/pinned-pages-registry"
import type { WordbankFilterState } from "@/app/sections/wordbank/wordbank-list-filters"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
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
    <div className="flex flex-col gap-5">
      {hasActiveFilters && filteredGroups.length === 0 ? <WordbankListEmpty onClearFilters={onClearFilters} /> : null}

      {filteredGroups.map((group) => (
        <section key={group.letter} className="flex flex-col gap-2">
          <h3 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">{group.letter}</h3>
          <div className="flex flex-wrap gap-2">
            {group.items.map((lemma) => {
              const displayWord = lemma.display_lemma?.trim() || lemma.lemma
              const unreadCount = unreadWordbankLemmaCounts.get(lemma.lemma) ?? 0
              return (
                <ContextMenu key={lemma.lemma}>
                  <ContextMenuTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="relative w-auto pr-3"
                      onClick={() => onSelectLemma(lemma.lemma)}
                    >
                      {displayWord}
                      <UnreadMarker count={unreadCount} displayWord={displayWord} />
                    </Button>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem
                      variant="destructive"
                      onSelect={() => onRequestDelete({ lemma: lemma.lemma, displayWord })}
                    >
                      <Trash2 />
                      Delete whole lemma
                    </ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              )
            })}
          </div>
        </section>
      ))}
    </div>
  )
}

function UnreadMarker({ count, displayWord }: { count: number; displayWord: string }) {
  if (count <= 0) return null
  if (count > 1) {
    return (
      <span className="bg-primary text-primary-foreground ml-2 inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] leading-5">
        {count}
      </span>
    )
  }
  return <span aria-label={`Pending verification for ${displayWord}`} className="bg-primary ml-2 inline-flex size-2.5 rounded-full" />
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
    const matchesPos = filters.posTags.length === 0 || filters.posTags.some((posTag) => lemmaPosTags.has(posTag))
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

export function PinnedGroupSection({
  pages,
  onSelectLemma,
}: {
  pages: PinnedPageMeta[]
  onSelectLemma: (lemma: string) => void
}) {
  return (
    <section className="flex flex-col gap-2">
      <div className="flex flex-wrap gap-2">
        {pages.map((page) => (
          <BuiltInReferenceCard
            key={page.sentinel}
            label={page.title}
            ariaLabel={`Open ${page.title} reference`}
            onClick={() => onSelectLemma(page.sentinel)}
          />
        ))}
      </div>
    </section>
  )
}

function BuiltInReferenceCard({
  label,
  ariaLabel,
  onClick,
}: {
  label: string
  ariaLabel: string
  onClick: () => void
}) {
  return (
    <Card className="overflow-hidden py-0 gap-0">
      <CardContent className="p-0">
        <Button
          type="button"
          variant="ghost"
          className="hover:bg-accent/60 h-auto w-auto items-center justify-between gap-3 rounded-none px-4 py-3 text-left"
          onClick={onClick}
          aria-label={ariaLabel}
        >
          <span className="text-sm font-semibold">{label}</span>
          <ChevronRight className="text-muted-foreground size-4 shrink-0" />
        </Button>
      </CardContent>
    </Card>
  )
}

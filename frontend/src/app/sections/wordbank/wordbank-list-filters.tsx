import { Check, ChevronsUpDown, Filter, FilterX } from "lucide-react"

import { isMultiWordLemma, posBadgeClass, semanticCategoryBadgeClass, type WordbankLemma } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Separator } from "@/components/ui/separator"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

export type WordbankFilterState = {
  posTags: string[]
  categories: string[]
}

type WordbankListFiltersProps = {
  lemmas: WordbankLemma[]
  filters: WordbankFilterState
  onFiltersChange: (filters: WordbankFilterState) => void
}

type FilterOption = {
  value: string
  label: string
}

const POS_LABELS: Record<string, string> = {
  ADJ: "Adjective",
  ADP: "Preposition",
  ADV: "Adverb",
  AUX: "Auxiliary",
  CCONJ: "Coordinating conjunction",
  DET: "Determiner",
  INTJ: "Interjection",
  NOUN: "Noun",
  NUM: "Number",
  PART: "Particle",
  PRON: "Pronoun",
  PROPN: "Proper noun",
  SCONJ: "Subordinating conjunction",
  VERB: "Verb",
  PHRASAL_VERB: "Phrasal verb",
  IDIOM: "Idiom",
}

export function WordbankListFilters({ lemmas, filters, onFiltersChange }: WordbankListFiltersProps) {
  const posOptions = collectPosOptions(lemmas)
  const categoryOptions = collectCategoryOptions(lemmas)
  const activeCount = filters.posTags.length + filters.categories.length

  if (posOptions.length === 0 && categoryOptions.length === 0) {
    return null
  }

  return (
    <div className="flex w-full flex-wrap items-center gap-2" data-wordbank-filters>
      {activeCount > 0 ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="text-muted-foreground size-8 shrink-0 rounded-md hover:bg-destructive/10 hover:text-destructive"
              onClick={() => onFiltersChange({ posTags: [], categories: [] })}
              aria-label="Clear filters"
            >
              <FilterX className="size-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            Clear filters
          </TooltipContent>
        </Tooltip>
      ) : (
        <div className="flex size-8 shrink-0 items-center justify-center">
          <Filter className="size-4 text-muted-foreground" />
        </div>
      )}
      <FilterMenu
        label="Word type"
        emptyLabel="No word types found."
        options={posOptions}
        selectedValues={filters.posTags}
        onToggle={(value) => {
          onFiltersChange({ ...filters, posTags: toggleFilterValue(filters.posTags, value) })
        }}
      />
      <FilterMenu
        label="Category"
        emptyLabel="No categories found."
        options={categoryOptions}
        selectedValues={filters.categories}
        searchable
        searchPlaceholder="Search categories..."
        onToggle={(value) => {
          onFiltersChange({ ...filters, categories: toggleFilterValue(filters.categories, value) })
        }}
      />
    </div>
  )
}

function FilterMenu({
  label,
  emptyLabel,
  options,
  selectedValues,
  searchable = false,
  searchPlaceholder,
  onToggle,
}: {
  label: string
  emptyLabel: string
  options: FilterOption[]
  selectedValues: string[]
  searchable?: boolean
  searchPlaceholder?: string
  onToggle: (value: string) => void
}) {
  const selectedItems = options.filter((option) => selectedValues.includes(option.value))

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-8 max-w-full justify-between border-dashed bg-transparent px-3 py-1 text-sm hover:bg-accent/50"
        >
          <div className="flex flex-wrap items-center gap-1.5 min-w-0">
            <span className="font-medium text-foreground shrink-0">{label}</span>
            {selectedValues.length > 0 && (
              <>
                <Separator orientation="vertical" className="mx-1.5 h-3.5 bg-muted-foreground/30 self-stretch hidden sm:block" />
                <div className="flex flex-wrap gap-1.5 items-center">
                  {selectedItems.map((item) => {
                    const isWordType = label === "Word type"
                    const badgeClasses = isWordType
                      ? `shrink-0 rounded-full px-2 py-0.5 text-xs font-normal leading-none border ${posBadgeClass(item.value)}`
                      : `shrink-0 rounded-full px-2 py-0.5 text-xs font-normal leading-none border ${semanticCategoryBadgeClass(item.value)}`

                    return (
                      <Badge
                        key={item.value}
                        variant={isWordType ? "default" : "outline"}
                        className={badgeClasses.trim()}
                      >
                        {item.label}
                      </Badge>
                    )
                  })}
                </div>
              </>
            )}
          </div>
          <ChevronsUpDown data-icon="inline-end" className="size-4 opacity-50 ml-2 shrink-0" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        align="start"
        className="w-72 p-0"
        onOpenAutoFocus={(e) => {
          if (window.matchMedia("(max-width: 767px)").matches) {
            e.preventDefault()
          }
        }}
      >
        <Command>
          {searchable ? <CommandInput placeholder={searchPlaceholder ?? `Search ${label.toLowerCase()}...`} /> : null}
          <CommandList className="max-h-72">
            <CommandEmpty>{emptyLabel}</CommandEmpty>
            <CommandGroup heading={label}>
              {options.map((option) => {
                const checked = selectedValues.includes(option.value)
                const isWordType = label === "Word type"
                const badgeClasses = isWordType
                  ? `shrink-0 rounded-full px-2 py-0.5 text-xs font-normal leading-none border ${posBadgeClass(option.value)}`
                  : `shrink-0 rounded-full px-2 py-0.5 text-xs font-normal leading-none border ${semanticCategoryBadgeClass(option.value)}`

                return (
                  <CommandItem
                    key={option.value}
                    value={option.label}
                    onSelect={() => onToggle(option.value)}
                    aria-checked={checked}
                  >
                    <Checkbox checked={checked} tabIndex={-1} aria-hidden="true" />
                    <div className="flex-1 min-w-0 py-0.5">
                      <Badge
                        variant={isWordType ? "default" : "outline"}
                        className={badgeClasses.trim()}
                      >
                        {option.label}
                      </Badge>
                    </div>
                    {checked ? <Check className="ml-2 shrink-0 size-4" /> : null}
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

function collectPosOptions(lemmas: WordbankLemma[]): FilterOption[] {
  const values = new Set<string>()
  let hasPhrasalVerb = false
  let hasIdiom = false
  for (const lemma of lemmas) {
    const isMwe = isMultiWordLemma(lemma.lemma)
    if (isMwe && (!lemma.pos_tags || lemma.pos_tags.length === 0)) {
      hasIdiom = true
    }
    for (const posTag of lemma.pos_tags ?? []) {
      const normalized = posTag.trim().toUpperCase()
      if (normalized) {
        if (isMwe) {
          if (normalized === "VERB" || normalized === "AUX") {
            hasPhrasalVerb = true
          } else {
            hasIdiom = true
          }
        } else {
          values.add(normalized)
        }
      }
    }
  }
  const options = [...values]
    .sort((left, right) => posLabel(left).localeCompare(posLabel(right), "da", { sensitivity: "base" }))
    .map((value) => ({ value, label: posLabel(value) }))

  if (hasPhrasalVerb) {
    options.push({ value: "PHRASAL_VERB", label: "Phrasal verb" })
  }
  if (hasIdiom) {
    options.push({ value: "IDIOM", label: "Idiom" })
  }
  return options
}

function collectCategoryOptions(lemmas: WordbankLemma[]): FilterOption[] {
  const values = new Set<string>()
  for (const lemma of lemmas) {
    for (const category of lemma.categories ?? []) {
      const normalized = category.trim()
      if (normalized) values.add(normalized)
    }
  }
  return [...values]
    .sort((left, right) => left.localeCompare(right, "da", { sensitivity: "base" }))
    .map((value) => ({ value, label: value }))
}

function toggleFilterValue(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

function posLabel(value: string): string {
  return POS_LABELS[value] ?? value.toLocaleLowerCase("da-DK").replace(/^\p{L}/u, (letter) => letter.toLocaleUpperCase("da-DK"))
}

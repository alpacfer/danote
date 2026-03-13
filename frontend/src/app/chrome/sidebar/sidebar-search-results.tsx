import { type LucideIcon } from "lucide-react"

import {
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"
import {
  previewText,
  type CORSearchGroup,
  type CORSearchVariant,
  type SavedNote,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type WordbankSearchItem,
} from "@/app/core"

import { SidebarCorResults } from "@/app/chrome/sidebar/sidebar-cor-results"
import { SidebarWordbankResults } from "@/app/chrome/sidebar/sidebar-wordbank-results"

type PageItem = {
  key: string
  label: string
  shortcut: string
  icon: LucideIcon
  onSelect: () => void
}

export type SidebarSearchResultsState = {
  normalizedQuery: string
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasNoteResults: boolean
  hasPageResults: boolean
}

export type SidebarSearchResultsData = {
  orderedWordbankResults: WordbankSearchItem[]
  displayVariantBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  addVariationBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  exactSavedVariationKeySet: Set<string>
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  variationCandidateCorIdSet: Set<string>
  matchingNotes: SavedNote[]
  matchingPageItems: PageItem[]
  isCorTranslationsLoading: boolean
  wordbankItemValue: (item: WordbankSearchItem) => string
  corVariantItemValue: (variant: CORSearchVariant) => string
}

export type SidebarSearchResultsActions = {
  onOpenSavedNote: (noteId: string) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
  onCloseSearch: () => void
}

type SidebarSearchResultsProps = {
  state: SidebarSearchResultsState
  data: SidebarSearchResultsData
  actions: SidebarSearchResultsActions
}

export function SidebarSearchResults({ state, data, actions }: SidebarSearchResultsProps) {
  return (
    <CommandList>
      {state.normalizedQuery && !state.hasAnyResults ? <CommandEmpty>No results found.</CommandEmpty> : null}
      {state.hasWordbankSectionResults ? (
        <CommandGroup heading="Wordbank">
          <SidebarWordbankResults
            orderedWordbankResults={data.orderedWordbankResults}
            displayVariantBySavedResult={data.displayVariantBySavedResult}
            addVariationBySavedResult={data.addVariationBySavedResult}
            exactSavedVariationKeySet={data.exactSavedVariationKeySet}
            normalizedQuery={state.normalizedQuery}
            wordbankItemValue={data.wordbankItemValue}
            onAddWordFromSearch={actions.onAddWordFromSearch}
            onOpenWordbankLemma={actions.onOpenWordbankLemma}
            onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
            onCloseSearch={actions.onCloseSearch}
          />
          <SidebarCorResults
            orderedCorSearchGroups={data.orderedCorSearchGroups}
            corSearchVariantsToRender={data.corSearchVariantsToRender}
            variationCandidateCorIdSet={data.variationCandidateCorIdSet}
            normalizedQuery={state.normalizedQuery}
            corVariantItemValue={data.corVariantItemValue}
            isTranslationsLoading={data.isCorTranslationsLoading}
            onAddWordFromSearch={actions.onAddWordFromSearch}
            onCloseSearch={actions.onCloseSearch}
          />
        </CommandGroup>
      ) : null}
      {(state.hasWordbankSectionResults || state.hasWordbankActions) && state.hasNoteResults ? <CommandSeparator /> : null}
      {state.hasNoteResults ? (
        <CommandGroup heading="Notes">
          {data.matchingNotes.map((note) => (
            <CommandItem
              key={`search-note-${note.id}`}
              value={`note-${note.id}`}
              onSelect={() => {
                actions.onOpenSavedNote(note.id)
                actions.onCloseSearch()
              }}
              className="flex-col items-start gap-0.5"
            >
              <span className="font-medium">{note.name}</span>
              <span className="text-muted-foreground line-clamp-2 text-xs">
                {previewText(note.text, 80)}
              </span>
            </CommandItem>
          ))}
        </CommandGroup>
      ) : null}
      {(state.hasWordbankSectionResults || state.hasWordbankActions || state.hasNoteResults) && state.hasPageResults ? <CommandSeparator /> : null}
      {state.hasPageResults ? (
        <CommandGroup heading="Pages">
          {data.matchingPageItems.map((item) => {
            const Icon = item.icon
            return (
              <CommandItem
                key={item.key}
                value={item.key}
                onSelect={() => {
                  item.onSelect()
                  actions.onCloseSearch()
                }}
              >
                <Icon />
                <span>{item.label}</span>
                <CommandShortcut>{item.shortcut}</CommandShortcut>
              </CommandItem>
            )
          })}
        </CommandGroup>
      ) : null}
    </CommandList>
  )
}

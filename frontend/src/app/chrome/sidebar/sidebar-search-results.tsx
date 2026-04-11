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
  normalizeSearchWord,
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
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"

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
  wordbankDidYouMean: string | null
  corDidYouMean: string | null
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
  onSetSearchQuery: (query: string) => void
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
  const dymSuggestion = state.wordbankDidYouMean ?? state.corDidYouMean

  // When wordbankDidYouMean is set, a wordbank item may still display an exact
  // match form (via its linked COR display variant). Those items belong in the
  // direct group rather than the corrected group.
  const directWordbankItems = !state.wordbankDidYouMean
    ? data.orderedWordbankResults
    : data.orderedWordbankResults.filter((item) => {
        const displayVariant = data.displayVariantBySavedResult.get(savedWordbankResultKey(item))?.variant
        if (displayVariant) {
          return normalizeSearchWord(displayVariant.form) === state.normalizedQuery
        }
        const matchSurface = normalizeSearchWord(item.match_surface ?? "")
        return matchSurface === state.normalizedQuery || normalizeSearchWord(item.lemma) === state.normalizedQuery
      })

  const correctedWordbankItems = !state.wordbankDidYouMean
    ? []
    : data.orderedWordbankResults.filter((item) => {
        const displayVariant = data.displayVariantBySavedResult.get(savedWordbankResultKey(item))?.variant
        if (displayVariant) {
          return normalizeSearchWord(displayVariant.form) !== state.normalizedQuery
        }
        const matchSurface = normalizeSearchWord(item.match_surface ?? "")
        return matchSurface !== state.normalizedQuery && normalizeSearchWord(item.lemma) !== state.normalizedQuery
      })

  const hasDirectWordbank = directWordbankItems.length > 0
  const hasDirectCor = !state.corDidYouMean && data.corSearchVariantsToRender.length > 0
  const hasDirectResults = hasDirectWordbank || hasDirectCor

  const hasCorrectedWordbank = correctedWordbankItems.length > 0
  const hasCorrectedCor = Boolean(state.corDidYouMean) && data.corSearchVariantsToRender.length > 0
  const hasCorrectedResults = hasCorrectedWordbank || hasCorrectedCor

  const hasWordbankSection = hasDirectResults || hasCorrectedResults

  return (
    <CommandList>
      {state.normalizedQuery && !state.hasAnyResults ? <CommandEmpty>No results found.</CommandEmpty> : null}

      {/* Direct results — exact query match */}
      {hasDirectResults ? (
        <CommandGroup heading="Wordbank">
          {hasDirectWordbank ? (
            <SidebarWordbankResults
              orderedWordbankResults={directWordbankItems}
              displayVariantBySavedResult={data.displayVariantBySavedResult}
              addVariationBySavedResult={data.addVariationBySavedResult}
              exactSavedVariationKeySet={data.exactSavedVariationKeySet}
              normalizedQuery={state.normalizedQuery}
              isTranslationsLoading={data.isCorTranslationsLoading}
              wordbankItemValue={data.wordbankItemValue}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onOpenWordbankLemma={actions.onOpenWordbankLemma}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
          {hasDirectCor ? (
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
          ) : null}
        </CommandGroup>
      ) : null}

      {/* DYM banner — between direct and corrected */}
      {dymSuggestion ? (
        <>
          {hasDirectResults ? <CommandSeparator /> : null}
          <CommandItem
            value="did-you-mean-suggestion"
            onSelect={() => actions.onSetSearchQuery(dymSuggestion)}
          >
            Did you mean &quot;{dymSuggestion}&quot;?
          </CommandItem>
          {hasCorrectedResults ? <CommandSeparator /> : null}
        </>
      ) : null}

      {/* Corrected results — for the DYM suggestion word */}
      {hasCorrectedResults ? (
        <CommandGroup heading="Wordbank">
          {hasCorrectedWordbank ? (
            <SidebarWordbankResults
              orderedWordbankResults={correctedWordbankItems}
              displayVariantBySavedResult={data.displayVariantBySavedResult}
              addVariationBySavedResult={data.addVariationBySavedResult}
              exactSavedVariationKeySet={data.exactSavedVariationKeySet}
              normalizedQuery={state.normalizedQuery}
              isTranslationsLoading={data.isCorTranslationsLoading}
              wordbankItemValue={data.wordbankItemValue}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onOpenWordbankLemma={actions.onOpenWordbankLemma}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
          {hasCorrectedCor ? (
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
          ) : null}
        </CommandGroup>
      ) : null}

      {(hasWordbankSection || state.hasWordbankActions) && state.hasNoteResults ? <CommandSeparator /> : null}
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
      {(hasWordbankSection || state.hasWordbankActions || state.hasNoteResults) && state.hasPageResults ? <CommandSeparator /> : null}
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

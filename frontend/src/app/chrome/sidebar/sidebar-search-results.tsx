import { Eye, type LucideIcon } from "lucide-react"

import {
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"
import { Skeleton } from "@/components/ui/skeleton"
import {
  previewText,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
  type SavedNote,
  type SentenceSearchPreviewResponse,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type WordbankSearchItem,
} from "@/app/core"

import { SidebarCorResults } from "@/app/chrome/sidebar/sidebar-cor-results"
import { SidebarEnResults } from "@/app/chrome/sidebar/sidebar-en-results"
import { SidebarSentenceResult } from "@/app/chrome/sidebar/sidebar-sentence-result"
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
  isSentenceMode: boolean
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasNoteResults: boolean
  hasPageResults: boolean
  wordbankDidYouMean: string | null
  corDidYouMean: string | null
}

export type SidebarSearchResultsData = {
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceSearchPreviewLoading: boolean
  orderedWordbankResults: WordbankSearchItem[]
  displayVariantBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  addVariationBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  exactSavedVariationKeySet: Set<string>
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  variationCandidateCorIdSet: Set<string>
  translatedEnCorSearchGroups: CORSearchGroup[]
  translatedEnCorVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  matchingNotes: SavedNote[]
  matchingPageItems: PageItem[]
  isCorTranslationsLoading: boolean
  wordbankItemValue: (item: WordbankSearchItem) => string
  corVariantItemValue: (variant: CORSearchVariant) => string
  translatedEnCorVariantItemValue: (variant: CORSearchVariant) => string
  enPosGroups: ENPosGroup[]
  isEnResolveLoading: boolean
  isEnTranslatedCorLoading: boolean
}

export type SidebarSearchResultsActions = {
  onAddSentenceFromSearch: (sourceText: string, englishTranslation: string | null) => Promise<void>
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
  if (state.isSentenceMode && (data.sentenceSearchPreview || data.isSentenceSearchPreviewLoading)) {
    return (
      <CommandList>
        <SidebarSentenceResult
          key={data.isSentenceSearchPreviewLoading ? "sentence-result-loading" : "sentence-result-ready"}
          sentenceSearchPreview={data.sentenceSearchPreview}
          isSentenceSearchPreviewLoading={data.isSentenceSearchPreviewLoading}
          onSaveSentence={actions.onAddSentenceFromSearch}
        />
      </CommandList>
    )
  }

  // Wordbank goes to the direct section when there's no DYM correction, or when
  // the current query is an exact form of a saved word (exactSavedVariationKeySet
  // is populated by the ranking hook for items whose lemma or match_surface equals
  // the normalized query).
  const hasDirectWordbank = data.orderedWordbankResults.length > 0
    && (!state.wordbankDidYouMean || data.exactSavedVariationKeySet.size > 0)
  const hasDirectCor = !state.corDidYouMean && data.corSearchVariantsToRender.length > 0
  const hasEnResults = data.translatedEnCorVariantsToRender.length > 0 || data.enPosGroups.length > 0
  const isEnLoading = data.isEnResolveLoading
  const isEnTranslating = data.isEnTranslatedCorLoading
  const isAnyEnLoading = isEnLoading || isEnTranslating
  // Phase 1: resolve in flight, no groups yet — show 2 default skeletons
  const showEnSkeletons = isEnLoading && !hasEnResults
  // Phase 2: COR translating, groups known — show N skeleton items matching entry count
  const showEnGroupSkeletons = isEnTranslating && data.enPosGroups.length > 0
  const showEnFallbackResults = data.enPosGroups.length > 0 && !isEnTranslating

  // Suppress DYM when COR has a direct match, EN has results, or EN is loading — the query is valid in some language.
  const dymSuggestion = (hasDirectCor || hasEnResults || isAnyEnLoading) ? null : (state.wordbankDidYouMean ?? state.corDidYouMean)
  const hasDirectResults = hasDirectWordbank || hasDirectCor

  const hasCorrectedWordbank = Boolean(state.wordbankDidYouMean)
    && data.orderedWordbankResults.length > 0
    && !hasDirectWordbank
    && !hasDirectCor
    && !hasEnResults
    && !isAnyEnLoading
  const hasCorrectedCor = Boolean(state.corDidYouMean) && data.corSearchVariantsToRender.length > 0 && !hasEnResults && !isAnyEnLoading
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
              orderedWordbankResults={data.orderedWordbankResults}
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
            className="mx-2"
          >
            Did you mean &quot;{dymSuggestion}&quot;?
          </CommandItem>
          {hasCorrectedResults ? <CommandSeparator /> : null}
        </>
      ) : null}

      {/* Corrected results — for the DYM suggestion word, COR first then saved */}
      {hasCorrectedResults ? (
        <CommandGroup heading="Wordbank">
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
          {hasCorrectedWordbank ? (
            <SidebarWordbankResults
              orderedWordbankResults={data.orderedWordbankResults}
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
        </CommandGroup>
      ) : null}

      {data.translatedEnCorVariantsToRender.length > 0 ? (
        <>
          {hasWordbankSection ? <CommandSeparator /> : null}
          <CommandGroup heading="Translated From English">
            <SidebarCorResults
              orderedCorSearchGroups={data.translatedEnCorSearchGroups}
              corSearchVariantsToRender={data.translatedEnCorVariantsToRender}
              variationCandidateCorIdSet={new Set<string>()}
              normalizedQuery={state.normalizedQuery}
              corVariantItemValue={data.translatedEnCorVariantItemValue}
              isTranslationsLoading={data.isEnResolveLoading}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onCloseSearch={actions.onCloseSearch}
            />
          </CommandGroup>
        </>
      ) : null}

      {(showEnGroupSkeletons || showEnFallbackResults) ? (
        <>
          {(hasWordbankSection || data.translatedEnCorVariantsToRender.length > 0) ? <CommandSeparator /> : null}
          <CommandGroup heading="Translated From English">
            {showEnGroupSkeletons ? (
              data.enPosGroups.map((_, i) => (
                <CommandItem
                  key={`en-skeleton-${i}`}
                  disabled
                  aria-hidden="true"
                  className="flex items-start justify-between gap-3"
                >
                  <div className="flex min-w-0 flex-col items-start gap-0.5">
                    <Skeleton className="h-3.5 w-24" />
                    <Skeleton className="h-3 w-36" />
                    <div className="mt-1 flex flex-wrap gap-1.5">
                      <Skeleton className="h-5 w-10 rounded-full" />
                    </div>
                  </div>
                  <Eye className="text-muted-foreground size-4 shrink-0 opacity-0" aria-hidden />
                </CommandItem>
              ))
            ) : (
              <SidebarEnResults
                enPosGroups={data.enPosGroups}
                originalQuery={state.normalizedQuery}
                onCloseSearch={actions.onCloseSearch}
              />
            )}
          </CommandGroup>
        </>
      ) : null}

      {showEnSkeletons ? (
        <>
          {hasWordbankSection ? <CommandSeparator /> : null}
          <CommandGroup heading="Translated From English">
            {[0, 1].map((i) => (
              <CommandItem
                key={`en-skeleton-${i}`}
                disabled
                aria-hidden="true"
                className="flex items-start justify-between gap-3"
              >
                <div className="flex min-w-0 flex-col items-start gap-0.5">
                  <Skeleton className="h-3.5 w-24" />
                  <Skeleton className="h-3 w-36" />
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    <Skeleton className="h-5 w-10 rounded-full" />
                  </div>
                </div>
                <Eye className="text-muted-foreground size-4 shrink-0 opacity-0" aria-hidden />
              </CommandItem>
            ))}
          </CommandGroup>
        </>
      ) : null}

      {(hasWordbankSection || hasEnResults || showEnSkeletons || state.hasWordbankActions) && state.hasNoteResults ? <CommandSeparator /> : null}
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
      {(hasWordbankSection || hasEnResults || showEnSkeletons || state.hasWordbankActions || state.hasNoteResults) && state.hasPageResults ? <CommandSeparator /> : null}
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

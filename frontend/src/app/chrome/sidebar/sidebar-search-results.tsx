import { Eye, type LucideIcon } from "lucide-react"

import {
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import { Skeleton } from "@/components/ui/skeleton"
import {
  normalizeSearchWord,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
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
  matchingPageItems: PageItem[]
  isCorTranslationsLoading: boolean
  wordbankItemValue: (item: WordbankSearchItem) => string
  corVariantItemValue: (variant: CORSearchVariant) => string
  translatedEnCorVariantItemValue: (variant: CORSearchVariant) => string
  enPosGroups: ENPosGroup[]
  isEnResolveLoading: boolean
  isEnTranslatedCorLoading: boolean
  enTranslatedCorSkeletonCount: number
}

export type SidebarSearchResultsActions = {
  onAddSentenceFromSearch: (sourceText: string, englishTranslation: string | null) => Promise<void>
  onSetSearchQuery: (query: string) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankLemmaRaw: (lemma: string) => void
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

function renderShortcut(shortcut: string) {
  const keys = shortcut.split("+")
  if (keys.length === 1) return <Kbd>{shortcut}</Kbd>
  return (
    <KbdGroup>
      {keys.map((k) => <Kbd key={k}>{k}</Kbd>)}
    </KbdGroup>
  )
}

function isSelfTranslatedCorVariant(variant: CORSearchVariant, normalizedQuery: string) {
  const translation = normalizeSearchWord(variant.saveable_translation ?? variant.lemma_translation ?? "")
  return Boolean(translation) && translation === normalizedQuery
}

export function SidebarSearchResults({ state, data, actions }: SidebarSearchResultsProps) {
  if (state.isSentenceMode) {
    return (
      <CommandList>
        <SidebarSentenceResult
          key={data.isSentenceSearchPreviewLoading ? "sentence-result-loading" : "sentence-result-ready"}
          sentenceSearchPreview={data.sentenceSearchPreview}
          isSentenceSearchPreviewLoading={data.isSentenceSearchPreviewLoading || !data.sentenceSearchPreview}
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
  const hasEnResults = data.translatedEnCorVariantsToRender.length > 0 || data.enPosGroups.length > 0
  const isAnyEnLoading = data.isEnResolveLoading || data.isEnTranslatedCorLoading
  const shouldResolveEnglishAmbiguity = hasEnResults || isAnyEnLoading
  const directCorSearchVariantsToRender = shouldResolveEnglishAmbiguity
    ? data.corSearchVariantsToRender.filter(({ variant }) => !isSelfTranslatedCorVariant(variant, state.normalizedQuery))
    : data.corSearchVariantsToRender
  const directCorSearchGroups = data.orderedCorSearchGroups.filter((group) =>
    directCorSearchVariantsToRender.some((item) => item.group === group),
  )
  const hasDirectCor = !state.corDidYouMean
    && directCorSearchVariantsToRender.length > 0
    && (!shouldResolveEnglishAmbiguity || !data.isCorTranslationsLoading)
  const showEnFallbackResults = data.enPosGroups.length > 0 && !isAnyEnLoading
  const hasTranslatedEnCorResults = data.translatedEnCorVariantsToRender.length > 0
  const showEnSkeletonResults = data.isEnTranslatedCorLoading && data.enTranslatedCorSkeletonCount > 0
  const hasTranslatedEnSection = hasTranslatedEnCorResults || showEnSkeletonResults || showEnFallbackResults

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
              onOpenWordbankLemma={actions.onOpenWordbankLemmaRaw}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
          {hasDirectCor ? (
            <SidebarCorResults
              orderedCorSearchGroups={directCorSearchGroups}
              corSearchVariantsToRender={directCorSearchVariantsToRender}
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
              onOpenWordbankLemma={actions.onOpenWordbankLemmaRaw}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          ) : null}
        </CommandGroup>
      ) : null}

      {hasTranslatedEnSection ? (
        <>
          {hasWordbankSection ? <CommandSeparator /> : null}
          <CommandGroup heading="Translated From English" className="animate-in fade-in-0 duration-150">
            {hasTranslatedEnCorResults ? (
              <SidebarCorResults
                orderedCorSearchGroups={data.translatedEnCorSearchGroups}
                corSearchVariantsToRender={data.translatedEnCorVariantsToRender}
                variationCandidateCorIdSet={new Set<string>()}
                normalizedQuery={state.normalizedQuery}
                showSourceWhenSameLemma={false}
                showTranslationLine={false}
                corVariantItemValue={data.translatedEnCorVariantItemValue}
                isTranslationsLoading={data.isEnResolveLoading}
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onCloseSearch={actions.onCloseSearch}
              />
            ) : null}
            {showEnSkeletonResults ? (
              Array.from({ length: data.enTranslatedCorSkeletonCount }, (_, i) => (
                <CommandItem
                  key={`en-skeleton-${i}`}
                  disabled
                  aria-hidden="true"
                  data-testid="search-en-skeleton"
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
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onCloseSearch={actions.onCloseSearch}
              />
            )}
          </CommandGroup>
        </>
      ) : null}

      {(hasWordbankSection || hasEnResults || isAnyEnLoading || state.hasWordbankActions) && state.hasPageResults ? <CommandSeparator /> : null}
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
                <span className="ml-auto">{renderShortcut(item.shortcut)}</span>
              </CommandItem>
            )
          })}
        </CommandGroup>
      ) : null}
    </CommandList>
  )
}

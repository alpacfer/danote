
import {
  CommandEmpty,
  CommandGroup,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command"
import {
  normalizeSearchWord,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
  type SentencebankSentence,
  type SentenceSearchPreviewResponse,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type WordbankSearchItem,
} from "@/app/core"

import { SidebarCorResults } from "@/app/chrome/sidebar/sidebar-cor-results"
import { SidebarEnResults } from "@/app/chrome/sidebar/sidebar-en-results"
import { SidebarSentenceResult } from "@/app/chrome/sidebar/sidebar-sentence-result"
import { SidebarSearchPendingSkeleton, SidebarSearchEnSkeletons } from "@/app/chrome/sidebar/sidebar-search-skeletons"
import { SidebarWordbankResults } from "@/app/chrome/sidebar/sidebar-wordbank-results"
import { SavedSentencesGroup } from "@/app/chrome/sidebar/sidebar-saved-sentences"
import { SidebarPagesResults } from "@/app/chrome/sidebar/sidebar-pages-results"
import { SearchSection } from "@/app/chrome/sidebar/sidebar-search-presentation"
import type { SidebarPageItem } from "@/app/chrome/sidebar/sidebar-page-items"
import type { SearchLanguageMode, SearchModeSwitchSuggestion } from "@/app/chrome/sidebar/sidebar-search-types"

export type SidebarSearchResultsState = {
  normalizedQuery: string
  isSentenceMode: boolean
  isNumberMode: boolean
  isMweMode?: boolean
  hasAnyResults: boolean
  hasWordbankSectionResults: boolean
  hasWordbankActions: boolean
  hasPageResults: boolean
  wordbankDidYouMean: string | null
  corDidYouMean: string | null
  enDidYouMean: string | null
  modeSwitchSuggestion: SearchModeSwitchSuggestion | null
}

export type SidebarSearchResultsData = {
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceSearchPreviewLoading: boolean
  matchedSavedSentences: SentencebankSentence[]
  orderedWordbankResults: WordbankSearchItem[]
  displayVariantBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  addVariationBySavedResult: Map<string, { group: CORSearchGroup; variant: CORSearchVariant }>
  exactSavedVariationKeySet: Set<string>
  orderedCorSearchGroups: CORSearchGroup[]
  corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  variationCandidateCorIdSet: Set<string>
  translatedEnCorSearchGroups: CORSearchGroup[]
  translatedEnCorVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }>
  matchingPageItems: SidebarPageItem[]
  isWordbankSearchLoading: boolean
  isCorLookupLoading: boolean
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
  onSwitchSearchMode: (mode: SearchLanguageMode) => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankLemmaRaw: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onOpenSentence: (id: number) => void
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



function isSelfTranslatedCorVariant(variant: CORSearchVariant, normalizedQuery: string) {
  const translation = normalizeSearchWord(variant.saveable_translation ?? variant.lemma_translation ?? "")
  return Boolean(translation) && translation === normalizedQuery
}

export function SidebarSearchResults({ state, data, actions }: SidebarSearchResultsProps) {
  const modeSwitchEntry = state.modeSwitchSuggestion ? (
    <CommandGroup data-search-note-group>
      <CommandItem
        value={state.modeSwitchSuggestion.value}
        onSelect={() => actions.onSwitchSearchMode(state.modeSwitchSuggestion!.targetMode)}
        data-search-note
      >
        <span>
          Try {state.modeSwitchSuggestion.targetMode === "en" ? "English" : "Danish"} instead
        </span>
        <span className="ml-auto hidden text-xs text-muted-foreground md:inline">
          {state.modeSwitchSuggestion.evidenceLabel}
        </span>
      </CommandItem>
    </CommandGroup>
  ) : null

  if (state.isSentenceMode) {
    if (state.isMweMode && data.sentenceSearchPreview && data.sentenceSearchPreview.mwe_cor_match) {
      // The backend normalizes mwe_pos_tag → UD ("VERB" for phrasal verbs and verbal
      // idioms). The frontend derives the "Phrasal verb" / "Idiom" badge from the
      // multi-word lemma (see primaryPosLabelForLemma in @/app/core), so fall back
      // to "VERB" rather than the retired "phrasal_verb" string when missing.
      const mwePosTag = data.sentenceSearchPreview.mwe_pos_tag ?? "VERB"
      // Polysemous MWE lemmas (e.g. "tage på" → put on / gain weight / go) come
      // back as `mwe_meanings` with one variant per sense. Monosemous MWEs may
      // either populate `mwe_meanings` with a single entry or just `mwe_cor_match`
      // (older API responses). Fall back to the single match when the list is empty.
      const meaningVariants = (data.sentenceSearchPreview.mwe_meanings?.length ?? 0) > 0
        ? data.sentenceSearchPreview.mwe_meanings!
        : [data.sentenceSearchPreview.mwe_cor_match]
      const mweVariants = meaningVariants.map((variant) => ({
        ...variant,
        pos_tag: variant.pos_tag ?? mwePosTag,
      }))
      const mweGroup: CORSearchGroup = {
        lemma: data.sentenceSearchPreview.mwe_lemma ?? mweVariants[0].lemma,
        gloss: data.sentenceSearchPreview.mwe_gloss,
        pos_tag: mwePosTag,
        variants: mweVariants,
      }
      const mweVariantsToRender = mweVariants.map((variant) => ({
        group: mweGroup,
        variant,
      }))

      return (
        <CommandList>
          <SearchSection heading="From the dictionary" material="discovery">
            <SidebarCorResults
              orderedCorSearchGroups={[mweGroup]}
              corSearchVariantsToRender={mweVariantsToRender}
              variationCandidateCorIdSet={new Set<string>()}
              normalizedQuery={state.normalizedQuery}
              corVariantItemValue={data.corVariantItemValue}
              isTranslationsLoading={false}
              onAddWordFromSearch={actions.onAddWordFromSearch}
              onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
              onCloseSearch={actions.onCloseSearch}
            />
          </SearchSection>
          {modeSwitchEntry ? (
            <>
              <CommandSeparator />
              {modeSwitchEntry}
            </>
          ) : null}
          {data.matchedSavedSentences.length > 0 ? (
            <>
              <CommandSeparator />
              <SavedSentencesGroup
                sentences={data.matchedSavedSentences}
                onOpen={(id) => { actions.onOpenSentence(id); actions.onCloseSearch() }}
              />
            </>
          ) : null}
        </CommandList>
      )
    }

    return (
      <CommandList>
        <SidebarSentenceResult
          key={data.isSentenceSearchPreviewLoading ? "sentence-result-loading" : "sentence-result-ready"}
          sentenceSearchPreview={data.sentenceSearchPreview}
          isSentenceSearchPreviewLoading={data.isSentenceSearchPreviewLoading || !data.sentenceSearchPreview}
          onSaveSentence={actions.onAddSentenceFromSearch}
        />
        {modeSwitchEntry ? (
          <>
            <CommandSeparator />
            {modeSwitchEntry}
          </>
        ) : null}
        {data.matchedSavedSentences.length > 0 ? (
          <>
            <CommandSeparator />
            <SavedSentencesGroup
              sentences={data.matchedSavedSentences}
              onOpen={(id) => { actions.onOpenSentence(id); actions.onCloseSearch() }}
            />
          </>
        ) : null}
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
  const hasDirectEnResults = hasEnResults && !state.enDidYouMean
  const isAnyEnLoading = data.isEnResolveLoading || data.isEnTranslatedCorLoading
  const shouldResolveEnglishAmbiguity = hasEnResults || isAnyEnLoading
  const translatedEnCorIds = new Set(
    data.translatedEnCorVariantsToRender.map(({ variant }) => variant.cor_id)
  )
  const directCorSearchVariantsToRender = shouldResolveEnglishAmbiguity
    ? data.corSearchVariantsToRender.filter(
        ({ variant }) =>
          !(
            isSelfTranslatedCorVariant(variant, state.normalizedQuery) &&
            (translatedEnCorIds.has(variant.cor_id) || variant.cor_id.endsWith(".SELF"))
          ),
      )
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

  // Suppress DYM when COR has a direct match, EN has direct results, or EN is loading — the query is valid in some language.
  const dymSuggestion = (hasDirectCor || hasDirectEnResults || isAnyEnLoading) ? null : (state.wordbankDidYouMean ?? state.corDidYouMean ?? state.enDidYouMean)
  const hasDirectResults = hasDirectWordbank || hasDirectCor
  const hasModeSwitchSuggestion = Boolean(state.modeSwitchSuggestion)

  const hasCorrectedWordbank = Boolean(state.wordbankDidYouMean)
    && data.orderedWordbankResults.length > 0
    && !hasDirectWordbank
    && !hasDirectCor
    && !hasEnResults
    && !isAnyEnLoading
  const hasCorrectedCor = Boolean(state.corDidYouMean) && data.corSearchVariantsToRender.length > 0 && !hasEnResults && !isAnyEnLoading
  const hasCorrectedResults = hasCorrectedWordbank || hasCorrectedCor

  const hasWordbankSection = hasDirectResults || hasCorrectedResults
  const hasFlowSpecificLoading = showEnSkeletonResults
  const isInitialSearchLoading = Boolean(state.normalizedQuery)
    && (data.isWordbankSearchLoading || data.isCorLookupLoading || data.isEnResolveLoading || data.isEnTranslatedCorLoading)
    && !hasDirectResults
    && !hasCorrectedResults
    && !hasTranslatedEnSection
    && !hasFlowSpecificLoading

  return (
    <CommandList>
      {state.normalizedQuery && !state.hasAnyResults && !isInitialSearchLoading ? (
        <CommandEmpty>Nothing found for “{state.normalizedQuery}”.</CommandEmpty>
      ) : null}

      {isInitialSearchLoading ? (
        <SearchSection
          heading="Looking it up"
          material="discovery"
          className="animate-in fade-in-0 duration-150"
        >
          <SidebarSearchPendingSkeleton />
        </SearchSection>
      ) : null}

      {/* Direct results — exact query match */}
      {hasDirectResults ? (
        <>
          {hasDirectWordbank ? (
            <SearchSection heading="In your notebook" material="word">
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
            </SearchSection>
          ) : null}
          {hasDirectWordbank && hasDirectCor ? <CommandSeparator /> : null}
          {hasDirectCor ? (
            <SearchSection heading="From the dictionary" material="discovery">
              <SidebarCorResults
                orderedCorSearchGroups={directCorSearchGroups}
                corSearchVariantsToRender={directCorSearchVariantsToRender}
                variationCandidateCorIdSet={data.variationCandidateCorIdSet}
                normalizedQuery={state.normalizedQuery}
                corVariantItemValue={data.corVariantItemValue}
                isTranslationsLoading={data.isCorTranslationsLoading}
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
                onCloseSearch={actions.onCloseSearch}
              />
            </SearchSection>
          ) : null}
        </>
      ) : null}

      {modeSwitchEntry ? (
        <>
          {hasDirectResults ? <CommandSeparator /> : null}
          {modeSwitchEntry}
          {(dymSuggestion || hasCorrectedResults || hasTranslatedEnSection || state.hasPageResults || data.matchedSavedSentences.length > 0)
            ? <CommandSeparator />
            : null}
        </>
      ) : null}

      {/* DYM banner — between direct and corrected */}
      {dymSuggestion ? (
        <>
          {hasDirectResults && !hasModeSwitchSuggestion ? <CommandSeparator /> : null}
          <CommandGroup data-search-note-group>
            <CommandItem
              value="did-you-mean-suggestion"
              onSelect={() => actions.onSetSearchQuery(dymSuggestion)}
              data-search-note
            >
              Did you mean “{dymSuggestion}”?
            </CommandItem>
          </CommandGroup>
          {hasCorrectedResults ? <CommandSeparator /> : null}
        </>
      ) : null}

      {/* Corrected results — for the DYM suggestion word, COR first then saved */}
      {hasCorrectedResults ? (
        <>
          {hasCorrectedCor ? (
            <SearchSection heading="From the dictionary" material="discovery">
              <SidebarCorResults
                orderedCorSearchGroups={data.orderedCorSearchGroups}
                corSearchVariantsToRender={data.corSearchVariantsToRender}
                variationCandidateCorIdSet={data.variationCandidateCorIdSet}
                normalizedQuery={state.normalizedQuery}
                corVariantItemValue={data.corVariantItemValue}
                isTranslationsLoading={data.isCorTranslationsLoading}
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
                onCloseSearch={actions.onCloseSearch}
              />
            </SearchSection>
          ) : null}
          {hasCorrectedCor && hasCorrectedWordbank ? <CommandSeparator /> : null}
          {hasCorrectedWordbank ? (
            <SearchSection heading="In your notebook" material="word">
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
            </SearchSection>
          ) : null}
        </>
      ) : null}

      {hasTranslatedEnSection ? (
        <>
          {hasWordbankSection ? <CommandSeparator /> : null}
          <SearchSection
            heading="From the dictionary"
            material="discovery"
            className="animate-in fade-in-0 duration-150"
          >
            {hasTranslatedEnCorResults ? (
              <SidebarCorResults
                orderedCorSearchGroups={data.translatedEnCorSearchGroups}
                corSearchVariantsToRender={data.translatedEnCorVariantsToRender}
                variationCandidateCorIdSet={new Set<string>()}
                normalizedQuery={state.normalizedQuery}
                showTranslationLine={false}
                corVariantItemValue={data.translatedEnCorVariantItemValue}
                isTranslationsLoading={data.isEnResolveLoading}
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onOpenWordbankMeaning={actions.onOpenWordbankMeaning}
                onCloseSearch={actions.onCloseSearch}
              />
            ) : null}
            {showEnSkeletonResults ? (
              <SidebarSearchEnSkeletons count={data.enTranslatedCorSkeletonCount} />
            ) : (
              <SidebarEnResults
                enPosGroups={data.enPosGroups}
                originalQuery={state.normalizedQuery}
                onAddWordFromSearch={actions.onAddWordFromSearch}
                onCloseSearch={actions.onCloseSearch}
              />
            )}
          </SearchSection>
        </>
      ) : null}

      {(hasWordbankSection || hasEnResults || isAnyEnLoading || state.hasWordbankActions) && state.hasPageResults ? <CommandSeparator /> : null}
      {state.hasPageResults ? (
        <SidebarPagesResults
          matchingPageItems={data.matchingPageItems}
          onCloseSearch={actions.onCloseSearch}
        />
      ) : null}

      {data.matchedSavedSentences.length > 0 ? (
        <>
          {(hasWordbankSection || hasEnResults || isAnyEnLoading || state.hasPageResults) ? <CommandSeparator /> : null}
          <SavedSentencesGroup
            sentences={data.matchedSavedSentences}
            onOpen={(id) => { actions.onOpenSentence(id); actions.onCloseSearch() }}
          />
        </>
      ) : null}
    </CommandList>
  )
}

import { useMemo, useState } from "react"

import { SidebarFooterActions } from "@/app/chrome/sidebar/sidebar-footer-actions"
import { SidebarNavigation } from "@/app/chrome/sidebar/sidebar-navigation"
import { useSidebarPageItems } from "@/app/chrome/sidebar/sidebar-page-items"
import { SidebarSearchInput } from "@/app/chrome/sidebar/sidebar-search-input"
import {
  SidebarSearchResults,
  type SidebarSearchResultsActions,
  type SidebarSearchResultsData,
  type SidebarSearchResultsState,
} from "@/app/chrome/sidebar/sidebar-search-results"
import { useSidebarCommandSelection } from "@/app/chrome/sidebar/use-sidebar-command-selection"
import { useSidebarHotkeys } from "@/app/chrome/sidebar/use-sidebar-hotkeys"
import { useSidebarLemmas } from "@/app/chrome/sidebar/use-sidebar-lemmas"
import { useSidebarSearch } from "@/app/chrome/sidebar/use-sidebar-search"
import { useSidebarSearchRanking } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import {
  type AppSection,
  type CORSearchVariant,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type SentencebankSentence,
  type WordbankLemma,
  type WordbankSearchItem,
} from "@/app/core"
import { CommandDialog } from "@/components/ui/command"
import {
  Sidebar,
  SidebarFooter,
  SidebarHeader,
  SidebarTrigger,
} from "@/components/ui/sidebar"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  sentences: SentencebankSentence[]
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
  unreadWordbankNotificationCount: number
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onSelectAccount: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankLemmaRaw: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onOpenSentence: (id: number) => void
  onAddSentenceToSentencebank: (sourceText: string, englishTranslation?: string | null) => Promise<void>
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
}

export function AppSidebar({
  activeSection,
  lemmas,
  sentences,
  wordbankCacheVersion,
  searchTranslationConfigVersion,
  unreadWordbankNotificationCount,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onSelectAccount,
  onOpenWordbankLemma,
  onOpenWordbankLemmaRaw,
  onOpenWordbankMeaning,
  onOpenSentence,
  onAddSentenceToSentencebank,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")

  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    isTrialLimitReached,
    isSentenceMode,
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    searchApiMatches,
    isWordbankSearchLoading,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorLookupLoading,
    isCorTranslationsLoading,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  } = useSidebarSearch({
    wordbankCacheVersion,
    searchTranslationConfigVersion,
  })
  const searchLemmas = useSidebarLemmas(lemmas, isSearchOpen)

  const matchedSavedSentences = useMemo(() => {
    const q = normalizedQuery.toLowerCase().trim()
    if (q.length < 2) return []
    return sentences
      .filter(
        (s) =>
          s.source_text.toLowerCase().includes(q) ||
          (s.english_translation ?? "").toLowerCase().includes(q),
      )
      .slice(0, 6)
  }, [sentences, normalizedQuery])

  useSidebarHotkeys({
    onToggleSearch: () => setIsSearchOpen((current) => !current),
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
    onSelectAccount,
  })

  const {
    variationCandidateCorIdSet,
    addVariationBySavedResult,
    displayVariantBySavedResult,
    exactSavedVariationKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults,
    hasWordbankActions,
  } = useSidebarSearchRanking({
    lemmas: searchLemmas,
    normalizedQuery,
    searchApiMatches,
    activeCorFormSearchResult,
  })

  const matchingPageItems = useSidebarPageItems({
    normalizedQuery,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
    onSelectAccount,
    onOpenWordbankLemma,
  })

  const hasPageResults = matchingPageItems.length > 0
  const hasTranslatedEnResults = activeEnTranslatedCorResults.corSearchVariantsToRender.length > 0
  const hasFallbackEnResults = activeEnTranslatedCorResults.fallbackEnPosGroups.length > 0
  const hasEnResults = hasTranslatedEnResults || hasFallbackEnResults
  const hasMatchedSentences = matchedSavedSentences.length > 0
  const hasAnyResults = isSentenceMode
    ? (Boolean(sentenceSearchPreview) || hasMatchedSentences)
    : (
        hasWordbankSectionResults
        || hasEnResults
        || hasPageResults
        || hasMatchedSentences
        || isWordbankSearchLoading
        || isCorLookupLoading
        || isEnResolveLoading
        || isEnTranslatedCorLoading
      )

  const { commandSelectionValue } = useSidebarCommandSelection({
    activeEnTranslatedCorResults,
    commandSelectionOverride,
    corDidYouMean,
    corSearchVariantsToRender,
    isSearchOpen,
    isSentenceMode,
    matchingPageItems,
    orderedCorSearchGroups,
    orderedWordbankResults,
    sentenceSearchPreview,
    setCommandSelectionOverride,
    wordbankDidYouMean,
  })

  const closeSearch = () => {
    setIsSearchOpen(false)
    setTimeout(() => {
      setSearchQuery("")
      setCommandSelectionOverride("")
    }, 200)
  }

  const saveSentenceFromSearch = (sourceText: string, englishTranslation: string | null = null) => {
    closeSearch()
    void onAddSentenceToSentencebank(sourceText, englishTranslation)
  }

  const searchResultState: SidebarSearchResultsState = {
    normalizedQuery,
    isSentenceMode,
    hasAnyResults,
    hasWordbankSectionResults,
    hasWordbankActions,
    hasPageResults,
    wordbankDidYouMean,
    corDidYouMean,
  }

  const searchResultData: SidebarSearchResultsData = {
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    matchedSavedSentences,
    orderedWordbankResults,
    displayVariantBySavedResult,
    addVariationBySavedResult,
    exactSavedVariationKeySet,
    orderedCorSearchGroups,
    corSearchVariantsToRender,
    variationCandidateCorIdSet,
    translatedEnCorSearchGroups: activeEnTranslatedCorResults.orderedCorSearchGroups,
    translatedEnCorVariantsToRender: activeEnTranslatedCorResults.corSearchVariantsToRender,
    matchingPageItems,
    isWordbankSearchLoading,
    isCorLookupLoading,
    isCorTranslationsLoading,
    wordbankItemValue: (item: WordbankSearchItem) => `wordbank-${savedWordbankResultKey(item)}`,
    corVariantItemValue: (variant: CORSearchVariant) => `cor-variant-${variant.cor_id}`,
    translatedEnCorVariantItemValue: (variant: CORSearchVariant) => `en-cor-${variant.lemma.toLowerCase()}-${variant.cor_id}`,
    enPosGroups: activeEnTranslatedCorResults.fallbackEnPosGroups,
    isEnResolveLoading: isEnResolveLoading,
    isEnTranslatedCorLoading: isEnTranslatedCorLoading,
    enTranslatedCorSkeletonCount,
  }

  const searchResultActions: SidebarSearchResultsActions = {
    onAddSentenceFromSearch: async (sourceText: string) => {
      saveSentenceFromSearch(sourceText, sentenceSearchPreview?.english_translation ?? null)
    },
    onSetSearchQuery: (query: string) => { setSearchQuery(query) },
    onOpenWordbankLemma,
    onOpenWordbankLemmaRaw,
    onOpenWordbankMeaning,
    onOpenSentence,
    onAddWordFromSearch,
    onCloseSearch: closeSearch,
  }

  return (
    <Sidebar variant="inset" collapsible="icon">
      <SidebarHeader>
        <div className="flex h-8 items-center gap-2 group-data-[collapsible=icon]:contents">
          <button
            type="button"
            className="truncate text-left text-base font-semibold hover:text-foreground/80 focus-visible:ring-ring rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-offset-2 group-data-[collapsible=icon]:sr-only"
            onClick={onSelectWordbank}
          >
            danote
          </button>
          <SidebarTrigger className="ml-auto size-8 cursor-ew-resize group-data-[collapsible=icon]:ml-0" />
        </div>
      </SidebarHeader>
      <CommandDialog
        open={isSearchOpen}
        onOpenChange={(open) => {
          setIsSearchOpen(open)
          if (!open) {
            setTimeout(() => {
              setSearchQuery("")
              setCommandSelectionOverride("")
            }, 200)
          }
        }}
        commandShouldFilter={false}
        commandValue={commandSelectionValue}
        onCommandValueChange={setCommandSelectionOverride}
        showCloseButton={false}
        className="rounded-xl"
        title="Search wordbank"
        description="Search saved words and local COR analyses."
      >
        <SidebarSearchInput
          value={searchQuery}
          sentenceSearchPreview={sentenceSearchPreview}
          onKeyDown={(event) => {
            if (
              event.key !== "Enter"
              || !isSentenceMode
              || !sentenceSearchPreview
              || isSentenceSearchPreviewLoading
              || sentenceSearchPreview.source_text === null
              || sentenceSearchPreview.status === "blocked"
            ) {
              return
            }

            event.preventDefault()
            event.stopPropagation()
            saveSentenceFromSearch(
              sentenceSearchPreview.source_text,
              sentenceSearchPreview.english_translation ?? null,
            )
          }}
          onValueChange={(value) => {
            setSearchQuery(value)
            setCommandSelectionOverride("")
          }}
        />
        {isTrialLimitReached ? (
          <div className="mx-3 my-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
            You&apos;ve used today&apos;s free-trial searches.{" "}
            <button
              type="button"
              className="font-medium underline underline-offset-2"
              onClick={() => {
                closeSearch()
                onSelectAccount()
              }}
            >
              Add your API keys
            </button>{" "}
            in Account for unlimited access. Resets tomorrow.
          </div>
        ) : null}
        <SidebarSearchResults
          state={searchResultState}
          data={searchResultData}
          actions={searchResultActions}
        />
      </CommandDialog>
      <SidebarNavigation
        activeSection={activeSection}
        unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        onSelectWordbank={onSelectWordbank}
        onSelectSentencebank={onSelectSentencebank}
        onSelectDeveloper={onSelectDeveloper}
        onOpenSearch={() => setIsSearchOpen(true)}
      />
      <SidebarFooter>
        <SidebarFooterActions activeSection={activeSection} onSelectAccount={onSelectAccount} />
      </SidebarFooter>
    </Sidebar>
  )
}

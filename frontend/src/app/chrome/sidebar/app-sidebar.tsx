import { useState } from "react"

import { ThemeToggleButton } from "@/app/chrome/theme-toggle-button"
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
  type SavedNote,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type WordbankLemma,
  type WordbankSearchItem,
} from "@/app/core"
import { Button } from "@/components/ui/button"
import { CommandDialog } from "@/components/ui/command"
import {
  Sidebar,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  wordbankCacheVersion: number
  searchTranslationConfigVersion: number
  savedNotes: SavedNote[]
  unreadWordbankNotificationCount: number
  onSelectPlayground: () => void
  onSelectNotes: () => void
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenWordbankMeaning: (lemma: string, meaningId: number) => void
  onOpenSavedNote: (noteId: string) => void
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
  wordbankCacheVersion,
  searchTranslationConfigVersion,
  savedNotes,
  unreadWordbankNotificationCount,
  onSelectPlayground,
  onSelectNotes,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
  onOpenWordbankMeaning,
  onOpenSavedNote,
  onAddSentenceToSentencebank,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")

  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    isSentenceMode,
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    matchingNotes,
    searchApiMatches,
    wordbankDidYouMean,
    corDidYouMean,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
    isEnResolveLoading,
    activeEnTranslatedCorResults,
    isEnTranslatedCorLoading,
  } = useSidebarSearch({
    savedNotes,
    wordbankCacheVersion,
    searchTranslationConfigVersion,
  })
  const searchLemmas = useSidebarLemmas(lemmas, isSearchOpen)

  useSidebarHotkeys({
    onToggleSearch: () => setIsSearchOpen((current) => !current),
    onSelectPlayground,
    onSelectNotes,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
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
    onSelectPlayground,
    onSelectNotes,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
  })

  const hasNoteResults = matchingNotes.length > 0
  const hasPageResults = matchingPageItems.length > 0
  const hasTranslatedEnResults = activeEnTranslatedCorResults.corSearchVariantsToRender.length > 0
  const hasFallbackEnResults = activeEnTranslatedCorResults.fallbackEnPosGroups.length > 0
  const hasEnResults = hasTranslatedEnResults || hasFallbackEnResults
  const hasAnyResults = isSentenceMode
    ? Boolean(sentenceSearchPreview)
    : (hasWordbankSectionResults || hasEnResults || hasNoteResults || hasPageResults || isEnResolveLoading || isEnTranslatedCorLoading)

  const { commandSelectionValue } = useSidebarCommandSelection({
    activeEnTranslatedCorResults,
    commandSelectionOverride,
    corDidYouMean,
    corSearchVariantsToRender,
    isSearchOpen,
    isSentenceMode,
    matchingNotes,
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
    hasNoteResults,
    hasPageResults,
    wordbankDidYouMean,
    corDidYouMean,
  }

  const searchResultData: SidebarSearchResultsData = {
    sentenceSearchPreview,
    isSentenceSearchPreviewLoading,
    orderedWordbankResults,
    displayVariantBySavedResult,
    addVariationBySavedResult,
    exactSavedVariationKeySet,
    orderedCorSearchGroups,
    corSearchVariantsToRender,
    variationCandidateCorIdSet,
    translatedEnCorSearchGroups: activeEnTranslatedCorResults.orderedCorSearchGroups,
    translatedEnCorVariantsToRender: activeEnTranslatedCorResults.corSearchVariantsToRender,
    matchingNotes,
    matchingPageItems,
    isCorTranslationsLoading,
    wordbankItemValue: (item: WordbankSearchItem) => `wordbank-${savedWordbankResultKey(item)}`,
    corVariantItemValue: (variant: CORSearchVariant) => `cor-variant-${variant.cor_id}`,
    translatedEnCorVariantItemValue: (variant: CORSearchVariant) => `en-cor-${variant.lemma.toLowerCase()}-${variant.cor_id}`,
    enPosGroups: activeEnTranslatedCorResults.fallbackEnPosGroups,
    isEnResolveLoading: isEnResolveLoading || isEnTranslatedCorLoading,
  }

  const searchResultActions: SidebarSearchResultsActions = {
    onAddSentenceFromSearch: async (sourceText: string) => {
      saveSentenceFromSearch(sourceText, sentenceSearchPreview?.english_translation ?? null)
    },
    onSetSearchQuery: (query: string) => { setSearchQuery(query) },
    onOpenSavedNote,
    onOpenWordbankLemma,
    onOpenWordbankMeaning,
    onAddWordFromSearch,
    onCloseSearch: closeSearch,
  }

  return (
    <Sidebar variant="inset">
      <SidebarHeader className="gap-2">
        <Button type="button" variant="outline" className="justify-between" onClick={() => setIsSearchOpen(true)}>
          Search...
          <span className="text-muted-foreground text-[10px] uppercase">Cmd/Ctrl+K</span>
        </Button>
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
          title="Search wordbank and notes"
          description="Search saved words, local COR analyses, and notes."
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
          <SidebarSearchResults
            state={searchResultState}
            data={searchResultData}
            actions={searchResultActions}
          />
        </CommandDialog>
      </SidebarHeader>
      <SidebarNavigation
        activeSection={activeSection}
        unreadWordbankNotificationCount={unreadWordbankNotificationCount}
        onSelectPlayground={onSelectPlayground}
        onSelectNotes={onSelectNotes}
        onSelectWordbank={onSelectWordbank}
        onSelectSentencebank={onSelectSentencebank}
        onSelectDeveloper={onSelectDeveloper}
      />
      <SidebarFooter>
        <ThemeToggleButton />
      </SidebarFooter>
    </Sidebar>
  )
}

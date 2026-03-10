import { useEffect, useMemo, useState } from "react"
import { BookOpen, NotebookPen, Settings } from "lucide-react"

import { ThemeToggleButton } from "@/app/chrome/theme-toggle-button"
import {
  SidebarSearchResults,
  type SidebarSearchResultsActions,
  type SidebarSearchResultsData,
  type SidebarSearchResultsState,
} from "@/app/chrome/sidebar/sidebar-search-results"
import { useSidebarHotkeys } from "@/app/chrome/sidebar/use-sidebar-hotkeys"
import { useSidebarSearch } from "@/app/chrome/sidebar/use-sidebar-search"
import { useSidebarSearchRanking } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import { savedWordbankResultKey } from "@/app/chrome/sidebar/use-sidebar-search-ranking"
import {
  BACKEND_URL,
  createApiClient,
  normalizeSearchWord,
  type AppSection,
  type CORSearchVariant,
  type SavedNote,
  type SearchSaveSeed,
  type SearchFeedbackContext,
  type WordbankLemma,
  type WordbankSearchItem,
} from "@/app/core"
import { Button } from "@/components/ui/button"
import { CommandDialog, CommandInput } from "@/components/ui/command"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"

export type AppSidebarProps = {
  activeSection: AppSection
  lemmas: WordbankLemma[]
  wordbankCacheVersion: number
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
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")
  const [searchSidebarLemmas, setSearchSidebarLemmas] = useState<WordbankLemma[]>([])
  const apiClient = useMemo(() => createApiClient({ backendUrl: BACKEND_URL }), [])

  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    activeCorFormSearchResult,
    isCorTranslationsLoading,
  } = useSidebarSearch({
    savedNotes,
    wordbankCacheVersion,
  })

  useEffect(() => {
    if (lemmas.length > 0 || !isSearchOpen || searchSidebarLemmas.length > 0) {
      return
    }

    let cancelled = false
    void (async () => {
      try {
        const payload = await apiClient.tryGetJson<{ items?: WordbankLemma[] }>("/api/wordbank/lemmas")
        if (!cancelled) {
          setSearchSidebarLemmas(payload?.items ?? [])
        }
      } catch {
        if (!cancelled) {
          setSearchSidebarLemmas([])
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [apiClient, isSearchOpen, lemmas.length, searchSidebarLemmas.length])

  useSidebarHotkeys({
    onToggleSearch: () => setIsSearchOpen((current) => !current),
    onSelectPlayground,
    onSelectNotes,
    onSelectWordbank,
    onSelectSentencebank,
    onSelectDeveloper,
  })

  const {
    savedLemmaKeySet,
    addVariationBySavedResult,
    displayVariantBySavedResult,
    exactSavedVariationKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults,
    hasWordbankActions,
  } = useSidebarSearchRanking({
    lemmas: lemmas.length > 0 ? lemmas : searchSidebarLemmas,
    normalizedQuery,
    searchApiMatches,
    activeCorFormSearchResult,
  })

  const matchingPageItems = useMemo(() => {
    const pageItems = [
      { key: "page-playground", label: "Playground", shortcut: "Alt+P", icon: NotebookPen, onSelect: onSelectPlayground },
      { key: "page-notes", label: "Notes", shortcut: "Alt+N", icon: BookOpen, onSelect: onSelectNotes },
      { key: "page-wordbank", label: "Wordbank", shortcut: "Alt+W", icon: BookOpen, onSelect: onSelectWordbank },
      { key: "page-sentencebank", label: "Sentencebank", shortcut: "Alt+S", icon: BookOpen, onSelect: onSelectSentencebank },
      { key: "page-developer", label: "Developer", shortcut: "Alt+D", icon: Settings, onSelect: onSelectDeveloper },
    ]
    if (!normalizedQuery) {
      return pageItems
    }
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [normalizedQuery, onSelectDeveloper, onSelectNotes, onSelectPlayground, onSelectSentencebank, onSelectWordbank])

  const hasNoteResults = matchingNotes.length > 0
  const hasPageResults = matchingPageItems.length > 0
  const hasAnyResults = hasWordbankSectionResults || hasNoteResults || hasPageResults

  const orderedCorVariantsToRender = useMemo(() => {
    const variants: CORSearchVariant[] = []
    for (const group of orderedCorSearchGroups) {
      for (const item of corSearchVariantsToRender) {
        if (item.group === group) {
          variants.push(item.variant)
        }
      }
    }
    return variants
  }, [corSearchVariantsToRender, orderedCorSearchGroups])

  const orderedCommandItemValues = useMemo(() => {
    const values: string[] = []
    for (const item of orderedWordbankResults) {
      values.push(`wordbank-${savedWordbankResultKey(item)}`)
    }
    for (const variant of orderedCorVariantsToRender) {
      values.push(`cor-variant-${variant.cor_id}`)
    }
    for (const note of matchingNotes) {
      values.push(`note-${note.id}`)
    }
    for (const page of matchingPageItems) {
      values.push(page.key)
    }
    return values
  }, [matchingNotes, matchingPageItems, orderedCorVariantsToRender, orderedWordbankResults])

  const commandSelectionValue = useMemo(() => {
    if (commandSelectionOverride && orderedCommandItemValues.includes(commandSelectionOverride)) {
      return commandSelectionOverride
    }
    return orderedCommandItemValues[0] ?? ""
  }, [commandSelectionOverride, orderedCommandItemValues])

  const searchResultState: SidebarSearchResultsState = {
    normalizedQuery,
    hasAnyResults,
    hasWordbankSectionResults,
    hasWordbankActions,
    hasNoteResults,
    hasPageResults,
  }

  const searchResultData: SidebarSearchResultsData = {
    orderedWordbankResults,
    displayVariantBySavedResult,
    addVariationBySavedResult,
    exactSavedVariationKeySet,
    orderedCorSearchGroups,
    corSearchVariantsToRender,
    savedLemmaKeySet,
    matchingNotes,
    matchingPageItems,
    isCorTranslationsLoading,
    wordbankItemValue: (item: WordbankSearchItem) => `wordbank-${savedWordbankResultKey(item)}`,
    corVariantItemValue: (variant: CORSearchVariant) => `cor-variant-${variant.cor_id}`,
  }

  const searchResultActions: SidebarSearchResultsActions = {
    onOpenSavedNote,
    onOpenWordbankLemma,
    onOpenWordbankMeaning,
    onAddWordFromSearch,
    onCloseSearch: () => {
      setIsSearchOpen(false)
      setSearchQuery("")
    },
  }

  return (
    <Sidebar variant="inset">
      <SidebarHeader className="gap-2">
        <p className="px-2 text-sm font-semibold">Danote</p>
        <Button type="button" variant="outline" className="justify-between" onClick={() => setIsSearchOpen(true)}>
          Search...
          <span className="text-muted-foreground text-[10px] uppercase">Cmd/Ctrl+K</span>
        </Button>
        <CommandDialog
          open={isSearchOpen}
          onOpenChange={(open) => {
            setIsSearchOpen(open)
            if (!open) {
              setSearchQuery("")
              setCommandSelectionOverride("")
            }
          }}
          commandShouldFilter={false}
          commandValue={commandSelectionValue}
          onCommandValueChange={setCommandSelectionOverride}
          title="Search wordbank and notes"
          description="Search saved words, local COR analyses, and notes."
        >
          <CommandInput
            placeholder="Search words and notes..."
            value={searchQuery}
            onValueChange={(value) => {
              setSearchQuery(normalizeSearchWord(value))
              setCommandSelectionOverride("")
            }}
            aria-label="command search"
          />
          <SidebarSearchResults
            state={searchResultState}
            data={searchResultData}
            actions={searchResultActions}
          />
        </CommandDialog>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton type="button" isActive={activeSection === "playground"} onClick={onSelectPlayground}>
                  <NotebookPen />
                  <span>Playground</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+P</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton type="button" isActive={activeSection === "notes"} onClick={onSelectNotes}>
                  <BookOpen />
                  <span>Notes</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+N</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton type="button" isActive={activeSection === "wordbank"} onClick={onSelectWordbank}>
                  <BookOpen />
                  <span>Wordbank</span>
                  {unreadWordbankNotificationCount > 0 ? (
                    <span className="bg-primary text-primary-foreground ml-auto inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] leading-5">
                      {unreadWordbankNotificationCount}
                    </span>
                  ) : (
                    <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+W</span>
                  )}
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton type="button" isActive={activeSection === "sentencebank"} onClick={onSelectSentencebank}>
                  <BookOpen />
                  <span>Sentencebank</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+S</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton type="button" isActive={activeSection === "developer"} onClick={onSelectDeveloper}>
                  <Settings />
                  <span>Developer</span>
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+D</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <ThemeToggleButton />
      </SidebarFooter>
    </Sidebar>
  )
}

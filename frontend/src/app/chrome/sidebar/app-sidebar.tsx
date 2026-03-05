import { useMemo, useState } from "react"
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
import {
  normalizeSearchWord,
  type AppSection,
  type CORSearchVariant,
  type SavedNote,
  type SearchFeedbackContext,
  type WordbankLemma,
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
  onSelectPlayground: () => void
  onSelectNotes: () => void
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onOpenWordbankLemma: (lemma: string) => void
  onOpenSavedNote: (noteId: string) => void
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
    },
  ) => Promise<string | null>
}

export function AppSidebar({
  activeSection,
  lemmas,
  wordbankCacheVersion,
  savedNotes,
  onSelectPlayground,
  onSelectNotes,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
  onOpenSavedNote,
  onAddWordFromSearch,
}: AppSidebarProps) {
  const [isSearchOpen, setIsSearchOpen] = useState(false)
  const [commandSelectionOverride, setCommandSelectionOverride] = useState("")

  const {
    searchQuery,
    setSearchQuery,
    normalizedQuery,
    matchingNotes,
    searchApiMatches,
    activeCorFormSearchResult,
  } = useSidebarSearch({
    savedNotes,
    wordbankCacheVersion,
  })

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
    addVariationBySavedLemma,
    displayVariantBySavedLemma,
    exactSavedVariationLemmaKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults,
    hasWordbankActions,
  } = useSidebarSearchRanking({
    lemmas,
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
    for (const { lemma } of orderedWordbankResults) {
      values.push(`wordbank-${normalizeSearchWord(lemma.lemma)}`)
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
    displayVariantBySavedLemma,
    addVariationBySavedLemma,
    exactSavedVariationLemmaKeySet,
    orderedCorSearchGroups,
    corSearchVariantsToRender,
    savedLemmaKeySet,
    matchingNotes,
    matchingPageItems,
    wordbankItemValue: (lemma: WordbankLemma) => `wordbank-${normalizeSearchWord(lemma.lemma)}`,
    corVariantItemValue: (variant: CORSearchVariant) => `cor-variant-${variant.cor_id}`,
  }

  const searchResultActions: SidebarSearchResultsActions = {
    onOpenSavedNote,
    onOpenWordbankLemma,
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
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+W</span>
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

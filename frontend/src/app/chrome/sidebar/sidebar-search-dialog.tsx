import { type Dispatch, type SetStateAction } from "react"

import { SidebarSearchInput } from "@/app/chrome/sidebar/sidebar-search-input"
import {
  SidebarSearchResults,
  type SidebarSearchResultsActions,
  type SidebarSearchResultsData,
  type SidebarSearchResultsState,
} from "@/app/chrome/sidebar/sidebar-search-results"
import type { SearchLanguageMode } from "@/app/chrome/sidebar/sidebar-search-types"
import { type SentenceSearchPreviewResponse } from "@/app/core"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { CommandDialog } from "@/components/ui/command"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"

type SidebarSearchDialogProps = {
  isOpen: boolean
  commandSelectionValue: string
  searchQuery: string
  searchLanguageMode: SearchLanguageMode
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceMode: boolean
  isSentenceSearchPreviewLoading: boolean
  isTrialLimitReached: boolean
  searchResultState: SidebarSearchResultsState
  searchResultData: SidebarSearchResultsData
  searchResultActions: SidebarSearchResultsActions
  setSearchQuery: Dispatch<SetStateAction<string>>
  setSearchLanguageMode: Dispatch<SetStateAction<SearchLanguageMode>>
  setCommandSelectionOverride: Dispatch<SetStateAction<string>>
  onCloseSearch: () => void
  onSelectAccount: () => void
  onSaveSentenceFromSearch: (sourceText: string, englishTranslation?: string | null) => void
  onOpenChange: (open: boolean) => void
}

export function SidebarSearchDialog({
  isOpen,
  commandSelectionValue,
  searchQuery,
  searchLanguageMode,
  sentenceSearchPreview,
  isSentenceMode,
  isSentenceSearchPreviewLoading,
  isTrialLimitReached,
  searchResultState,
  searchResultData,
  searchResultActions,
  setSearchQuery,
  setSearchLanguageMode,
  setCommandSelectionOverride,
  onCloseSearch,
  onSelectAccount,
  onSaveSentenceFromSearch,
  onOpenChange,
}: SidebarSearchDialogProps) {
  return (
    <CommandDialog
      open={isOpen}
      onOpenChange={onOpenChange}
      commandShouldFilter={false}
      commandValue={commandSelectionValue}
      onCommandValueChange={setCommandSelectionOverride}
      showCloseButton={false}
      className="rounded-xl max-md:bottom-0 max-md:left-0 max-md:top-auto max-md:max-h-dvh max-md:w-screen max-md:max-w-none max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-none max-md:rounded-t-xl max-md:border-0 max-md:border-t max-md:shadow-2xl max-md:duration-0"
      overlayClassName="max-md:duration-0"
      commandClassName="max-md:flex-col-reverse max-md:rounded-none max-md:rounded-t-xl max-md:[&_[cmdk-group-heading]]:text-sm max-md:[&_[data-slot=command-input-wrapper]]:shrink-0 max-md:[&_[data-slot=command-input-wrapper]>svg]:mt-0 max-md:[&_[data-slot=command-input-wrapper]>svg]:self-center max-md:[&_[data-slot=command-input-suffix]]:inset-y-0 max-md:[&_[data-slot=command-input-suffix]]:items-center max-md:[&_[data-slot=command-input-suffix]]:pt-0 max-md:[&_[data-slot=command-input-wrapper]_svg]:h-5 max-md:[&_[data-slot=command-input-wrapper]_svg]:w-5 max-md:[&_[data-slot=command-input]]:!h-auto max-md:[&_[data-slot=command-input]]:text-base max-md:[&_[data-slot=command-input-overlay]]:text-base max-md:[&_[cmdk-item]]:py-3 max-md:[&_[cmdk-item]]:text-base max-md:[&_[cmdk-item]_svg]:h-5 max-md:[&_[cmdk-item]_svg]:w-5 max-md:[&_[data-slot=command-list]]:max-h-[70dvh] max-md:[&_[data-slot=command-list]]:min-h-0 max-md:[&_[data-slot=command-list]]:flex-initial max-md:[&_[data-slot=command-list]]:pt-3 max-md:[&_[data-slot=command-list]]:pb-2"
      title="Search wordbank"
      description="Search saved words and local COR analyses."
    >
      <SidebarSearchInput
        value={searchQuery}
        searchLanguageMode={searchLanguageMode}
        onLanguageModeChange={(mode) => {
          setSearchLanguageMode(mode)
          setCommandSelectionOverride("")
        }}
        sentenceSearchPreview={sentenceSearchPreview}
        onCloseSearch={onCloseSearch}
        wordbankDidYouMean={searchResultState.wordbankDidYouMean}
        corDidYouMean={searchResultState.corDidYouMean}
        enDidYouMean={searchResultState.enDidYouMean}
        isSentenceMode={isSentenceMode}
        onKeyDown={(event) => {
          if (
            event.key !== "Enter"
            || !isSentenceMode
            || !sentenceSearchPreview
            || sentenceSearchPreview.is_multi_word_expression
            || isSentenceSearchPreviewLoading
            || sentenceSearchPreview.source_text === null
            || sentenceSearchPreview.status === "blocked"
          ) {
            return
          }

          event.preventDefault()
          event.stopPropagation()
          onSaveSentenceFromSearch(
            sentenceSearchPreview.source_text,
            sentenceSearchPreview.english_translation ?? null,
          )
        }}
        onValueChange={(value) => {
          setSearchQuery(value)
          setCommandSelectionOverride("")
        }}
      />
      <div className="sr-only">
        <span id="search-language-label" className="sr-only">Search language</span>
        <ToggleGroup
          type="single"
          value={searchLanguageMode}
          onValueChange={(value) => {
            if (value === "da" || value === "en") {
              setSearchLanguageMode(value)
              setCommandSelectionOverride("")
            }
          }}
          aria-labelledby="search-language-label"
          variant="outline"
          size="sm"
          spacing={0}
          className="w-full"
        >
          <ToggleGroupItem value="da" className="flex-1">Danish</ToggleGroupItem>
          <ToggleGroupItem value="en" className="flex-1">English</ToggleGroupItem>
        </ToggleGroup>
      </div>
      {isTrialLimitReached ? (
        <Alert className="mx-3 my-2 w-auto bg-accent/45">
          <AlertDescription className="block text-xs text-accent-foreground">
            You&apos;ve used today&apos;s free-trial searches.{" "}
            <Button
              type="button"
              variant="link"
              size="xs"
              className="h-auto p-0 text-xs"
              onClick={() => {
                onCloseSearch()
                onSelectAccount()
              }}
            >
              Add your API keys
            </Button>{" "}
            in Account for unlimited access. Resets tomorrow.
          </AlertDescription>
        </Alert>
      ) : null}
      <SidebarSearchResults
        state={searchResultState}
        data={searchResultData}
        actions={searchResultActions}
      />
    </CommandDialog>
  )
}

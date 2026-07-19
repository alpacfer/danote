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
      className="top-[46%] max-h-[82vh] w-[calc(100%_-_2rem)] max-w-[42rem] rounded-2xl border-border/80 shadow-floating sm:max-w-[42rem] max-md:bottom-0 max-md:left-0 max-md:top-auto max-md:max-h-dvh max-md:w-screen max-md:max-w-none max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-none max-md:rounded-t-2xl max-md:border-0 max-md:border-t max-md:duration-0"
      overlayClassName="max-md:duration-0"
      commandClassName="rounded-2xl max-md:rounded-none max-md:rounded-t-2xl"
      title="Find a word or sentence"
      description="Search Danish words, English meanings, or whole sentences."
    >
      <div data-search-folio className="flex min-h-0 flex-1 flex-col max-md:flex-col-reverse">
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
        {isTrialLimitReached ? (
          <Alert className="mx-4 my-2 w-auto bg-accent/45 md:mx-5">
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
      </div>
    </CommandDialog>
  )
}

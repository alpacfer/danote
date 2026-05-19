import { type Dispatch, type SetStateAction } from "react"

import { SidebarSearchInput } from "@/app/chrome/sidebar/sidebar-search-input"
import {
  SidebarSearchResults,
  type SidebarSearchResultsActions,
  type SidebarSearchResultsData,
  type SidebarSearchResultsState,
} from "@/app/chrome/sidebar/sidebar-search-results"
import { type SentenceSearchPreviewResponse } from "@/app/core"
import { CommandDialog } from "@/components/ui/command"

type SidebarSearchDialogProps = {
  isOpen: boolean
  commandSelectionValue: string
  searchQuery: string
  sentenceSearchPreview: SentenceSearchPreviewResponse | null
  isSentenceMode: boolean
  isSentenceSearchPreviewLoading: boolean
  isTrialLimitReached: boolean
  searchResultState: SidebarSearchResultsState
  searchResultData: SidebarSearchResultsData
  searchResultActions: SidebarSearchResultsActions
  setSearchQuery: Dispatch<SetStateAction<string>>
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
  sentenceSearchPreview,
  isSentenceMode,
  isSentenceSearchPreviewLoading,
  isTrialLimitReached,
  searchResultState,
  searchResultData,
  searchResultActions,
  setSearchQuery,
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
      className="rounded-xl max-md:top-auto max-md:bottom-0 max-md:left-0 max-md:h-[100dvh] max-md:w-screen max-md:max-w-none max-md:translate-x-0 max-md:translate-y-0 max-md:rounded-none max-md:border-x-0 max-md:border-b-0"
      commandClassName="max-md:flex-col-reverse max-md:rounded-none max-md:pb-[env(safe-area-inset-bottom)] max-md:[&_[cmdk-group-heading]]:text-sm max-md:[&_[data-slot=command-input-wrapper]]:m-3 max-md:[&_[data-slot=command-input-wrapper]]:min-h-12 max-md:[&_[data-slot=command-input-wrapper]]:shrink-0 max-md:[&_[data-slot=command-input-wrapper]>svg]:mt-0 max-md:[&_[data-slot=command-input-wrapper]>svg]:self-center max-md:[&_[data-slot=command-input-wrapper]_svg]:h-5 max-md:[&_[data-slot=command-input-wrapper]_svg]:w-5 max-md:[&_[data-slot=command-input]]:!h-auto max-md:[&_[data-slot=command-input]]:text-base max-md:[&_[cmdk-item]]:py-3 max-md:[&_[cmdk-item]]:text-base max-md:[&_[cmdk-item]_svg]:h-5 max-md:[&_[cmdk-item]_svg]:w-5 max-md:[&_[data-slot=command-list]]:max-h-none max-md:[&_[data-slot=command-list]]:flex-1 max-md:[&_[data-slot=command-list]]:pb-2"
      title="Search wordbank"
      description="Search saved words and local COR analyses."
    >
      <SidebarSearchInput
        value={searchQuery}
        sentenceSearchPreview={sentenceSearchPreview}
        onCancelSearch={onCloseSearch}
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
        <div className="mx-3 my-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-300">
          You&apos;ve used today&apos;s free-trial searches.{" "}
          <button
            type="button"
            className="font-medium underline underline-offset-2"
            onClick={() => {
              onCloseSearch()
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
  )
}

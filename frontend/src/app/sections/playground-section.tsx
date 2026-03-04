import { Eye, Plus } from "lucide-react"

import { NotesEditor } from "@/components/notes-editor"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import {
  addLoadingKey,
  PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS,
  type AnalyzedToken,
  type HighlightPopoverState,
  type PhrasePopoverState,
  type SaveDialogMode,
  type WordActionSuggestion,
} from "@/app/core"
import type { HighlightSpan } from "@/lib/token-highlights"

export type PlaygroundSectionProps = {
  isSaveDialogOpen: boolean
  saveDialogMode: SaveDialogMode
  noteNameDraft: string
  duplicateNameConflictNoteId: string | null
  onSaveDialogOpenChange: (open: boolean) => void
  onNoteNameDraftChange: (value: string) => void
  onSaveDialogSubmit: () => void
  onResolveDuplicateName: () => void
  phrasePopover: PhrasePopoverState
  onPhrasePopoverOpenChange: (open: boolean) => void
  isGeneratingPhraseTranslation: boolean
  phraseTranslation: string | null
  generatePhraseTranslationError: string | null
  isSavingSentence: boolean
  isSelectedPhraseSaved: boolean
  onAddSentenceFromPhrase: () => void
  highlightPopover: HighlightPopoverState
  onHighlightPopoverOpenChange: (open: boolean) => void
  popoverDisplayToken: AnalyzedToken | null
  showPopoverLemma: boolean
  popoverLemmaText: string | null
  popoverMetadataBadges: Array<{ key: string; label: string; className: string }>
  showTranslationSkeleton: boolean
  popoverIsNoun: boolean
  popoverIsVerbLike: boolean
  generateTranslationError: string | null
  popoverTranslation: string | null
  popoverPrimaryAction: WordActionSuggestion | null
  addingTokens: Record<string, boolean>
  onOpenWordbankFromPopover: () => void
  onAddTokenFromPopover: () => void
  noteText: string
  noteHighlights: HighlightSpan[]
  analysisError: string | null
  onNoteTextChange: (nextText: string) => void
  onHighlightClick: (payload: { tokenIndex: number; left: number; lineTop: number; lineBottom: number }) => void
  onTextSelectionSettled: (payload: { selectedText: string; left: number; lineTop: number; lineBottom: number } | null) => void
}

export function PlaygroundSection({
  isSaveDialogOpen,
  saveDialogMode,
  noteNameDraft,
  duplicateNameConflictNoteId,
  onSaveDialogOpenChange,
  onNoteNameDraftChange,
  onSaveDialogSubmit,
  onResolveDuplicateName,
  phrasePopover,
  onPhrasePopoverOpenChange,
  isGeneratingPhraseTranslation,
  phraseTranslation,
  generatePhraseTranslationError,
  isSavingSentence,
  isSelectedPhraseSaved,
  onAddSentenceFromPhrase,
  highlightPopover,
  onHighlightPopoverOpenChange,
  popoverDisplayToken,
  showPopoverLemma,
  popoverLemmaText,
  popoverMetadataBadges,
  showTranslationSkeleton,
  popoverIsNoun,
  popoverIsVerbLike,
  generateTranslationError,
  popoverTranslation,
  popoverPrimaryAction,
  addingTokens,
  onOpenWordbankFromPopover,
  onAddTokenFromPopover,
  noteText,
  noteHighlights,
  analysisError,
  onNoteTextChange,
  onHighlightClick,
  onTextSelectionSettled,
}: PlaygroundSectionProps) {
  return (
    <div className="space-y-4">
      <Dialog
        open={isSaveDialogOpen}
        onOpenChange={onSaveDialogOpenChange}
      >
        <DialogContent>
          <form
            className="space-y-4"
            onSubmit={(event) => {
              event.preventDefault()
              onSaveDialogSubmit()
            }}
          >
            <DialogHeader>
              <DialogTitle>{saveDialogMode === "create_new" ? "Create new note" : "Save note"}</DialogTitle>
              {saveDialogMode === "create_new" ? (
                <DialogDescription>
                  The current note will be saved. Creating a new note clears the editor.
                </DialogDescription>
              ) : (
                <DialogDescription>Name this note to store text and analysis.</DialogDescription>
              )}
            </DialogHeader>
            {saveDialogMode === "create_new" ? (
              <div className="space-y-2">
                <Label htmlFor="save-note-name-new">New note name</Label>
                <Input
                  id="save-note-name-new"
                  value={noteNameDraft}
                  onChange={(event) => {
                    onNoteNameDraftChange(event.target.value)
                  }}
                  placeholder="My Danish note copy"
                  autoComplete="off"
                  autoFocus
                />
              </div>
            ) : (
              <div className="space-y-2">
                <Label htmlFor="save-note-name">Note name</Label>
                <Input
                  id="save-note-name"
                  value={noteNameDraft}
                  onChange={(event) => {
                    onNoteNameDraftChange(event.target.value)
                  }}
                  placeholder="My Danish note"
                  autoComplete="off"
                  autoFocus
                />
              </div>
            )}
            {duplicateNameConflictNoteId ? (
              <p className="text-muted-foreground text-sm">
                {saveDialogMode === "create_new"
                  ? "A note with this title already exists. Use it or change the name."
                  : "A note with this title already exists. Overwrite it or change the name."}
              </p>
            ) : null}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onSaveDialogOpenChange(false)}>
                Cancel
              </Button>
              {duplicateNameConflictNoteId ? (
                <Button
                  type="button"
                  onClick={onResolveDuplicateName}
                >
                  {saveDialogMode === "create_new" ? "Use existing note" : "Overwrite existing"}
                </Button>
              ) : null}
              {saveDialogMode === "create_new" ? (
                <Button type="submit">Create new note</Button>
              ) : (
                <Button type="submit">Save</Button>
              )}
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      <div className="relative">
        <Popover
          open={phrasePopover.open && Boolean(phrasePopover.selectedText)}
          onOpenChange={onPhrasePopoverOpenChange}
        >
          <PopoverAnchor asChild>
            <button
              type="button"
              aria-hidden="true"
              tabIndex={-1}
              className="pointer-events-none fixed size-px opacity-0"
              style={{
                left: phrasePopover.left,
                top: phrasePopover.side === "bottom" ? phrasePopover.lineBottom : phrasePopover.lineTop,
              }}
            />
          </PopoverAnchor>
          <PopoverContent
            side={phrasePopover.side}
            align="start"
            sideOffset={8}
            onOpenAutoFocus={(event) => {
              event.preventDefault()
            }}
            className={`${PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS} space-y-2`}
          >
            <div className="flex items-start justify-between gap-3">
              <div className={`space-y-1 ${PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS} min-w-0`}>
                <p className="text-sm font-semibold leading-snug break-words">{phrasePopover.selectedText}</p>
                {isGeneratingPhraseTranslation && !phraseTranslation ? (
                  <Skeleton data-testid="phrase-translation-skeleton" className="h-4 w-28" />
                ) : generatePhraseTranslationError ? (
                  <p className="text-destructive text-xs">{generatePhraseTranslationError}</p>
                ) : phraseTranslation ? (
                  <p className="text-muted-foreground text-sm break-words">{phraseTranslation}</p>
                ) : (
                  <p className="text-muted-foreground text-xs">No translation available.</p>
                )}
              </div>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="inline-flex">
                    <Button
                      type="button"
                      variant="default"
                      size="icon-sm"
                      aria-label="Add to sentencebank"
                      disabled={isSavingSentence || isSelectedPhraseSaved}
                      onClick={onAddSentenceFromPhrase}
                    >
                      <Plus />
                    </Button>
                  </span>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={6}>
                  <p>{isSelectedPhraseSaved ? "Already in sentencebank" : isSavingSentence ? "Saving..." : "Add to sentencebank"}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </PopoverContent>
        </Popover>
        <Popover
          open={highlightPopover.open && Boolean(popoverDisplayToken)}
          onOpenChange={onHighlightPopoverOpenChange}
        >
          <PopoverAnchor asChild>
            <button
              type="button"
              aria-hidden="true"
              tabIndex={-1}
              className="pointer-events-none fixed size-px opacity-0"
              style={{
                left: highlightPopover.left,
                top: highlightPopover.side === "bottom" ? highlightPopover.lineBottom : highlightPopover.lineTop,
              }}
            />
          </PopoverAnchor>
          <PopoverContent
            side={highlightPopover.side}
            align="start"
            sideOffset={8}
            onOpenAutoFocus={(event) => {
              event.preventDefault()
            }}
            className="w-fit max-w-[calc(100vw-1rem)] space-y-3"
          >
            {popoverDisplayToken && (
              <>
                <div className="space-y-1">
                  <div className="flex items-center gap-1.5">
                    {popoverDisplayToken.surface_token ? (
                      <div className="flex flex-wrap items-baseline gap-1.5">
                        <p className="text-2xl font-bold leading-tight">{popoverDisplayToken.surface_token}</p>
                        {showPopoverLemma ? (
                          <p className="text-muted-foreground text-sm font-normal leading-tight">({popoverLemmaText})</p>
                        ) : null}
                      </div>
                    ) : (
                      <Skeleton data-testid="word-skeleton" className="h-7 w-28" />
                    )}
                    <div className="flex shrink-0 flex-nowrap items-center gap-1">
                      {popoverMetadataBadges.map((badge) => (
                        <Badge key={badge.key} variant="secondary" className={`text-xs ${badge.className}`.trim()}>
                          {badge.label}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  {showTranslationSkeleton ? (
                    <Skeleton
                      data-testid={popoverIsNoun ? "noun-translation-skeleton" : popoverIsVerbLike ? "verb-translation-skeleton" : "translation-skeleton"}
                      className="h-4 w-24"
                    />
                  ) : generateTranslationError ? (
                    <p className="text-destructive text-xs">{generateTranslationError}</p>
                  ) : popoverTranslation ? (
                    <p className="text-muted-foreground text-sm">{popoverTranslation}</p>
                  ) : (
                    <p className="text-muted-foreground text-xs">No translation available.</p>
                  )}
                  <div className="mt-2.5 flex items-center justify-end gap-2">
                    {popoverPrimaryAction?.action_type === "open_wordbank" ? (
                      <Tooltip><TooltipTrigger asChild><span className="inline-flex">
                        <Button type="button" variant="default" size="icon-sm" aria-label="Open in wordbank" disabled={!popoverPrimaryAction.lemma} onClick={onOpenWordbankFromPopover}><Eye /></Button>
                      </span></TooltipTrigger><TooltipContent side="right" sideOffset={6}><p>Open in wordbank</p></TooltipContent></Tooltip>
                    ) : popoverPrimaryAction ? (
                      <Tooltip><TooltipTrigger asChild><span className="inline-flex">
                        <Button type="button" variant="default" size="icon-sm" aria-label={popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"} disabled={Boolean(addingTokens[addLoadingKey(popoverDisplayToken)])} onClick={onAddTokenFromPopover}><Plus /></Button>
                      </span></TooltipTrigger><TooltipContent side="right" sideOffset={6}><p>{popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"}</p></TooltipContent></Tooltip>
                    ) : null}
                  </div>
                </div>
              </>
            )}
          </PopoverContent>
        </Popover>
        <NotesEditor
          id="lesson-notes"
          placeholder="Type lesson notes here..."
          value={noteText}
          highlights={noteHighlights}
          onChange={onNoteTextChange}
          onHighlightClick={onHighlightClick}
          onTextSelectionSettled={onTextSelectionSettled}
        />
        <p className="text-muted-foreground absolute right-3 bottom-2 text-xs" aria-label="note-character-count">
          {noteText.length}
        </p>
      </div>
      {analysisError && (
        <p className="text-destructive mt-2 text-sm" role="alert">
          {analysisError}
        </p>
      )}
    </div>
  )
}

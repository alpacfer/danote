import { Plus } from "lucide-react"

import { PHRASE_POPOVER_MAX_TEXT_WIDTH_CLASS } from "@/app/core"
import type { PlaygroundSectionProps } from "@/app/sections/playground/playground-section-types"
import { Button } from "@/components/ui/button"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

type PlaygroundPhrasePopoverProps = Pick<
  PlaygroundSectionProps,
  | "phrasePopover"
  | "onPhrasePopoverOpenChange"
  | "isGeneratingPhraseTranslation"
  | "phraseTranslation"
  | "generatePhraseTranslationError"
  | "isSavingSentence"
  | "isSelectedPhraseSaved"
  | "onAddSentenceFromPhrase"
>

export function PlaygroundPhrasePopover({
  phrasePopover,
  onPhrasePopoverOpenChange,
  isGeneratingPhraseTranslation,
  phraseTranslation,
  generatePhraseTranslationError,
  isSavingSentence,
  isSelectedPhraseSaved,
  onAddSentenceFromPhrase,
}: PlaygroundPhrasePopoverProps) {
  return (
    <Popover open={phrasePopover.open && Boolean(phrasePopover.selectedText)} onOpenChange={onPhrasePopoverOpenChange}>
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
  )
}

import { Eye, Plus } from "lucide-react"

import { addLoadingKey } from "@/app/core"
import type { PlaygroundSectionProps } from "@/app/sections/playground/playground-section-types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Popover, PopoverAnchor, PopoverContent } from "@/components/ui/popover"
import { Skeleton } from "@/components/ui/skeleton"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"

type PlaygroundHighlightPopoverProps = Pick<
  PlaygroundSectionProps,
  | "highlightPopover"
  | "onHighlightPopoverOpenChange"
  | "popoverDisplayToken"
  | "showPopoverLemma"
  | "popoverLemmaText"
  | "popoverMetadataBadges"
  | "showTranslationSkeleton"
  | "popoverIsNoun"
  | "popoverIsVerbLike"
  | "generateTranslationError"
  | "popoverTranslation"
  | "popoverPrimaryAction"
  | "addingTokens"
  | "onOpenWordbankFromPopover"
  | "onAddTokenFromPopover"
>

export function PlaygroundHighlightPopover({
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
}: PlaygroundHighlightPopoverProps) {
  return (
    <Popover open={highlightPopover.open && Boolean(popoverDisplayToken)} onOpenChange={onHighlightPopoverOpenChange}>
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
        {popoverDisplayToken ? (
          <div className="space-y-1">
            <div className="flex items-center gap-1.5">
              {popoverDisplayToken.surface_token ? (
                <div className="flex flex-wrap items-baseline gap-1.5">
                  <p className="text-2xl font-bold leading-tight">{popoverDisplayToken.surface_token}</p>
                  {showPopoverLemma ? <p className="text-muted-foreground text-sm font-normal leading-tight">({popoverLemmaText})</p> : null}
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
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex">
                      <Button
                        type="button"
                        variant="default"
                        size="icon-sm"
                        aria-label="Open in wordbank"
                        disabled={!popoverPrimaryAction.lemma}
                        onClick={onOpenWordbankFromPopover}
                      >
                        <Eye />
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={6}><p>Open in wordbank</p></TooltipContent>
                </Tooltip>
              ) : popoverPrimaryAction ? (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <span className="inline-flex">
                      <Button
                        type="button"
                        variant="default"
                        size="icon-sm"
                        aria-label={popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"}
                        disabled={Boolean(addingTokens[addLoadingKey(popoverDisplayToken)])}
                        onClick={onAddTokenFromPopover}
                      >
                        <Plus />
                      </Button>
                    </span>
                  </TooltipTrigger>
                  <TooltipContent side="right" sideOffset={6}>
                    <p>{popoverPrimaryAction.action_type === "add_variation" ? "Add variation" : "Add to wordbank"}</p>
                  </TooltipContent>
                </Tooltip>
              ) : null}
            </div>
          </div>
        ) : null}
      </PopoverContent>
    </Popover>
  )
}

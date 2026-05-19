import type { ReactElement } from "react"

import type { VerbFormLabel } from "@/app/core/morphology"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"
import { Languages, Loader2, MessageSquareQuote, MoreHorizontal, RefreshCw, Sparkles, TableProperties } from "lucide-react"

const VERB_TENSES: VerbFormLabel[] = ["Infinitive", "Present", "Past", "Past participle", "Imperative"]

type WordbankScopeContextMenuProps = {
  children: ReactElement
  isRerunningVerification: boolean
  onRerunVerification: () => void
  isFindingAlternativeTranslations: boolean
  onFindAlternativeTranslations: () => void
  isRethinkingCategories: boolean
  onRethinkCategories: () => void
  isGeneratingExample?: boolean
  onGenerateExample?: (tense?: VerbFormLabel) => void
  isVerb?: boolean
  canCompleteVariations?: boolean
  completeVariationsLabel?: string
  isCompletingVariations?: boolean
  onCompleteVariations?: () => void
}

export function WordbankScopeContextMenu({
  children,
  isRerunningVerification,
  onRerunVerification,
  isFindingAlternativeTranslations,
  onFindAlternativeTranslations,
  isRethinkingCategories,
  onRethinkCategories,
  isGeneratingExample = false,
  onGenerateExample,
  isVerb = false,
  canCompleteVariations = false,
  completeVariationsLabel = "Complete variations",
  isCompletingVariations = false,
  onCompleteVariations,
}: WordbankScopeContextMenuProps) {
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>
        <div className="group relative">
          {children}
          <div className="absolute top-2 right-2 z-10">
            <DropdownMenu>
              <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label="More options"
                  className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100 data-[state=open]:opacity-100"
                >
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                <DropdownMenuItem
                  disabled={isRerunningVerification}
                  onSelect={onRerunVerification}
                >
                  {isRerunningVerification ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                  {isRerunningVerification ? "Rerunning verification..." : "Rerun verification"}
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={isFindingAlternativeTranslations}
                  onSelect={onFindAlternativeTranslations}
                >
                  {isFindingAlternativeTranslations ? <Loader2 className="animate-spin" /> : <Languages />}
                  {isFindingAlternativeTranslations ? "Finding alternative translations..." : "Find alternative translations"}
                </DropdownMenuItem>
                <DropdownMenuItem
                  disabled={isRethinkingCategories}
                  onSelect={onRethinkCategories}
                >
                  {isRethinkingCategories ? <Loader2 className="animate-spin" /> : <Sparkles />}
                  {isRethinkingCategories ? "Rethinking categories..." : "Rethink categories"}
                </DropdownMenuItem>
                {onGenerateExample && isVerb ? (
                  <DropdownMenuSub>
                    <DropdownMenuSubTrigger disabled={isGeneratingExample} className="gap-2">
                      {isGeneratingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
                      {isGeneratingExample ? "Generating example..." : "Generate example"}
                    </DropdownMenuSubTrigger>
                    <DropdownMenuSubContent>
                      {VERB_TENSES.map((tense) => (
                        <DropdownMenuItem key={tense} onSelect={() => onGenerateExample(tense)}>
                          {tense}
                        </DropdownMenuItem>
                      ))}
                    </DropdownMenuSubContent>
                  </DropdownMenuSub>
                ) : onGenerateExample ? (
                  <DropdownMenuItem
                    disabled={isGeneratingExample}
                    onSelect={() => onGenerateExample()}
                  >
                    {isGeneratingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
                    {isGeneratingExample ? "Generating example..." : "Generate example"}
                  </DropdownMenuItem>
                ) : null}
                {onCompleteVariations ? (
                  <>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      disabled={isCompletingVariations || !canCompleteVariations}
                      onSelect={onCompleteVariations}
                    >
                      {isCompletingVariations ? <Loader2 className="animate-spin" /> : <TableProperties />}
                      {isCompletingVariations ? "Completing variations..." : completeVariationsLabel}
                    </DropdownMenuItem>
                  </>
                ) : null}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem
          disabled={isRerunningVerification}
          onSelect={onRerunVerification}
        >
          {isRerunningVerification ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          {isRerunningVerification ? "Rerunning verification..." : "Rerun verification"}
        </ContextMenuItem>
        <ContextMenuItem
          disabled={isFindingAlternativeTranslations}
          onSelect={onFindAlternativeTranslations}
        >
          {isFindingAlternativeTranslations ? <Loader2 className="animate-spin" /> : <Languages />}
          {isFindingAlternativeTranslations ? "Finding alternative translations..." : "Find alternative translations"}
        </ContextMenuItem>
        <ContextMenuItem
          disabled={isRethinkingCategories}
          onSelect={onRethinkCategories}
        >
          {isRethinkingCategories ? <Loader2 className="animate-spin" /> : <Sparkles />}
          {isRethinkingCategories ? "Rethinking categories..." : "Rethink categories"}
        </ContextMenuItem>
        {onGenerateExample && isVerb ? (
          <ContextMenuSub>
            <ContextMenuSubTrigger disabled={isGeneratingExample} className="gap-2">
              {isGeneratingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
              {isGeneratingExample ? "Generating example..." : "Generate example"}
            </ContextMenuSubTrigger>
            <ContextMenuSubContent>
              {VERB_TENSES.map((tense) => (
                <ContextMenuItem key={tense} onSelect={() => onGenerateExample(tense)}>
                  {tense}
                </ContextMenuItem>
              ))}
            </ContextMenuSubContent>
          </ContextMenuSub>
        ) : onGenerateExample ? (
          <ContextMenuItem
            disabled={isGeneratingExample}
            onSelect={() => onGenerateExample()}
          >
            {isGeneratingExample ? <Loader2 className="animate-spin" /> : <MessageSquareQuote />}
            {isGeneratingExample ? "Generating example..." : "Generate example"}
          </ContextMenuItem>
        ) : null}
        {onCompleteVariations ? (
          <>
            <ContextMenuSeparator />
            <ContextMenuItem
              disabled={isCompletingVariations || !canCompleteVariations}
              onSelect={onCompleteVariations}
            >
              {isCompletingVariations ? <Loader2 className="animate-spin" /> : <TableProperties />}
              {isCompletingVariations ? "Completing variations..." : completeVariationsLabel}
            </ContextMenuItem>
          </>
        ) : null}
      </ContextMenuContent>
    </ContextMenu>
  )
}

import type { ReactElement } from "react"

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { Languages, Loader2, RefreshCw, Sparkles, TableProperties } from "lucide-react"

type WordbankScopeContextMenuProps = {
  children: ReactElement
  isRerunningVerification: boolean
  onRerunVerification: () => void
  isFindingAlternativeTranslations: boolean
  onFindAlternativeTranslations: () => void
  isRethinkingCategories: boolean
  onRethinkCategories: () => void
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
  canCompleteVariations = false,
  completeVariationsLabel = "Complete variations",
  isCompletingVariations = false,
  onCompleteVariations,
}: WordbankScopeContextMenuProps) {
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
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

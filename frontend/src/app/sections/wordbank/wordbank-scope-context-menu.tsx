import type { ReactElement } from "react"

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"

type WordbankScopeContextMenuProps = {
  children: ReactElement
  isRethinkingCategories: boolean
  onRethinkCategories: () => void
  canCompleteVariations?: boolean
  completeVariationsLabel?: string
  isCompletingVariations?: boolean
  onCompleteVariations?: () => void
}

export function WordbankScopeContextMenu({
  children,
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
          disabled={isRethinkingCategories}
          onSelect={onRethinkCategories}
        >
          {isRethinkingCategories ? "Rethinking categories..." : "Rethink categories"}
        </ContextMenuItem>
        {onCompleteVariations ? (
          <ContextMenuItem
            disabled={isCompletingVariations || !canCompleteVariations}
            onSelect={onCompleteVariations}
          >
            {isCompletingVariations ? "Completing variations..." : completeVariationsLabel}
          </ContextMenuItem>
        ) : null}
      </ContextMenuContent>
    </ContextMenu>
  )
}

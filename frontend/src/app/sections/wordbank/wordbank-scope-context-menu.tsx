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
  isCompletingVariations?: boolean
  onCompleteVariations?: () => void
}

export function WordbankScopeContextMenu({
  children,
  isRethinkingCategories,
  onRethinkCategories,
  canCompleteVariations = false,
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
        {canCompleteVariations && onCompleteVariations ? (
          <ContextMenuItem
            disabled={isCompletingVariations}
            onSelect={onCompleteVariations}
          >
            {isCompletingVariations ? "Completing variations..." : "Complete variations"}
          </ContextMenuItem>
        ) : null}
      </ContextMenuContent>
    </ContextMenu>
  )
}

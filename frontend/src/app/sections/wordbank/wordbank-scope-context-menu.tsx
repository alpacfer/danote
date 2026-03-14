import type { ReactElement } from "react"

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"

type WordbankScopeContextMenuProps = {
  children: ReactElement
  isBusy: boolean
  onRethinkCategories: () => void
}

export function WordbankScopeContextMenu({
  children,
  isBusy,
  onRethinkCategories,
}: WordbankScopeContextMenuProps) {
  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem
          disabled={isBusy}
          onSelect={onRethinkCategories}
        >
          {isBusy ? "Rethinking categories..." : "Rethink categories"}
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

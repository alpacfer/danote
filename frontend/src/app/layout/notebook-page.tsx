import type { ReactNode } from "react"

import { cn } from "@/lib/utils"

type NotebookPageProps = {
  children: ReactNode
  className?: string
}

export function NotebookPage({ children, className }: NotebookPageProps) {
  return (
    <div className="danote-notebook-viewport min-h-0 flex-1 overflow-y-auto">
      <div
        className={cn(
          "danote-notebook-sheet mx-auto flex min-h-full w-full max-w-7xl flex-col",
          className,
        )}
        data-notebook-sheet
      >
        {children}
      </div>
    </div>
  )
}

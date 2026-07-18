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
        className="danote-notebook-sheet flex min-h-full w-full flex-col"
        data-notebook-sheet
      >
        <div
          className={cn(
            "danote-notebook-content mx-auto flex w-full max-w-7xl flex-1 flex-col",
            className,
          )}
          data-notebook-content
        >
          {children}
        </div>
      </div>
    </div>
  )
}

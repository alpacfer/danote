import type { ReactNode } from "react"

import { ScrollArea } from "@/components/ui/scroll-area"

type PinnedPageLayoutProps = {
  title: string
  description?: ReactNode
  children: ReactNode
}

export function PinnedPageLayout({ title, description, children }: PinnedPageLayoutProps) {
  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-6 pr-2">
          <header className="space-y-1">
            <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
            {description ? (
              <p className="text-muted-foreground text-sm">{description}</p>
            ) : null}
          </header>
          {children}
        </div>
      </ScrollArea>
    </div>
  )
}

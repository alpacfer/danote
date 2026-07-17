import type { ReactNode } from "react"

type PinnedPageLayoutProps = {
  title: string
  description?: ReactNode
  children: ReactNode
}

export function PinnedPageLayout({ title, description, children }: PinnedPageLayoutProps) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
      <div className="min-h-0 min-w-0 flex-1 overflow-y-auto">
        <div className="flex w-full min-w-0 max-w-full flex-col gap-6 pr-2">
          <header className="flex min-w-0 flex-col gap-1">
            <h1 className="font-section-title text-xl leading-tight font-semibold">{title}</h1>
            {description ? (
              <p className="text-muted-foreground text-sm">{description}</p>
            ) : null}
          </header>
          {children}
        </div>
      </div>
    </div>
  )
}

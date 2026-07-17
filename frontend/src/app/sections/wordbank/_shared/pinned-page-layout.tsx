import type { ReactNode } from "react"

type PinnedPageLayoutProps = {
  title: string
  description?: ReactNode
  children: ReactNode
}

export function PinnedPageLayout({ title, description, children }: PinnedPageLayoutProps) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-6" data-grid-page="wordbank-reference">
          <header className="flex min-w-0 flex-col gap-2" data-grid-anchor="rule">
            <h1 className="font-section-title flex min-h-8 items-center text-xl leading-8 font-semibold">{title}</h1>
            {description ? (
              <p className="text-muted-foreground min-h-6 text-sm leading-6">{description}</p>
            ) : null}
          </header>
          {children}
    </div>
  )
}

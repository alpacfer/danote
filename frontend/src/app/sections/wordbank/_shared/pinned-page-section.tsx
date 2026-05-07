import type { ReactNode } from "react"

import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { cn } from "@/lib/utils"

type PinnedPageSectionProps = {
  title?: string
  description?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
}

export function PinnedPageSection({
  title,
  description,
  children,
  className,
  contentClassName,
}: PinnedPageSectionProps) {
  return (
    <Card className={cn("py-5", className)}>
      {title || description ? (
        <CardHeader className="gap-1">
          {title ? <h2 className="text-base font-semibold leading-tight">{title}</h2> : null}
          {description ? <p className="text-muted-foreground text-sm">{description}</p> : null}
        </CardHeader>
      ) : null}
      <CardContent className={cn(contentClassName)}>{children}</CardContent>
    </Card>
  )
}

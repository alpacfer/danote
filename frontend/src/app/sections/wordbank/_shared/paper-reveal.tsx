import type { ComponentProps, ReactNode } from "react"

import { HoverCardContent } from "@/components/ui/hover-card"
import { cn } from "@/lib/utils"

type MaterialRole = "reference" | "word"

type PaperRevealProps = Omit<
  ComponentProps<typeof HoverCardContent>,
  "align" | "collisionPadding" | "side" | "sideOffset"
> & {
  children: ReactNode
  material: MaterialRole
  materialTone?: string
}

export function PaperReveal({
  children,
  className,
  material,
  materialTone,
  ...props
}: PaperRevealProps) {
  return (
    <HoverCardContent
      align="start"
      side="top"
      sideOffset={0}
      collisionPadding={16}
      className={cn("p-0", className)}
      data-material={material}
      data-material-tone={materialTone}
      data-index-stock
      data-paper-reveal
      data-paper-stock
      {...props}
    >
      {children}
    </HoverCardContent>
  )
}

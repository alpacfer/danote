import { Children } from "react"

import { cn } from "@/lib/utils"

function Kbd({ className, ...props }: React.ComponentProps<"kbd">) {
  return (
    <kbd
      data-slot="kbd"
      className={cn(
        "inline-flex h-5 w-fit min-w-5 items-center justify-center gap-1 rounded-sm bg-muted px-1 font-sans text-xs font-medium text-muted-foreground select-none transition-colors",
        "hover:bg-accent hover:text-accent-foreground",
        "group-hover:bg-accent group-hover:text-accent-foreground",
        "[&_svg:not([class*='size-'])]:size-3",
        "[[data-slot=tooltip-content]_&]:bg-background/20 [[data-slot=tooltip-content]_&]:text-background dark:[[data-slot=tooltip-content]_&]:bg-background/10",
        className
      )}
      {...props}
    />
  )
}

function KbdGroup({ className, children, ...props }: React.ComponentProps<"div">) {
  const childArray = Children.toArray(children)
  const withSeparators = childArray.flatMap((child, i) =>
    i === 0
      ? [child]
      : [
          <span
            key={`sep-${i}`}
            className="text-muted-foreground/60 select-none text-[10px] transition-colors group-hover:text-accent-foreground"
          >
            +
          </span>,
          child,
        ]
  )
  return (
    <kbd
      data-slot="kbd-group"
      className={cn("group inline-flex items-center gap-0.5", className)}
      {...props}
    >
      {withSeparators}
    </kbd>
  )
}

export { Kbd, KbdGroup }

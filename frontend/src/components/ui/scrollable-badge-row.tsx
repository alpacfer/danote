import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"

import { cn } from "@/lib/utils"

type ScrollableBadgeRowProps = {
  children: ReactNode
  className?: string
  /**
   * Tailwind class providing the fade gradient's solid color (e.g. `from-card`,
   * `from-background`). The fades only appear when the row overflows. Defaults
   * to `from-background`.
   */
  fadeFromClass?: string
  /**
   * Optional `data-testid` for tests.
   */
  testId?: string
}

/**
 * A horizontally scrollable badge row that, when its children overflow the
 * available width, exposes left/right arrow controls (revealing roughly one
 * badge at a time) and subtle fade gradients on each side. When everything
 * fits, it renders as a plain flex row.
 */
export function ScrollableBadgeRow({
  children,
  className,
  fadeFromClass = "from-background",
  testId,
}: ScrollableBadgeRowProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)
  const [canLeft, setCanLeft] = useState(false)
  const [canRight, setCanRight] = useState(false)

  const updateOverflow = useCallback(() => {
    const el = scrollerRef.current
    if (!el) return
    const max = el.scrollWidth - el.clientWidth
    setCanLeft(el.scrollLeft > 1)
    setCanRight(el.scrollLeft < max - 1)
  }, [])

  useEffect(() => {
    const el = scrollerRef.current
    if (!el) return
    updateOverflow()
    const ro = new ResizeObserver(updateOverflow)
    ro.observe(el)
    for (const child of Array.from(el.children)) ro.observe(child as Element)
    el.addEventListener("scroll", updateOverflow, { passive: true })
    return () => {
      ro.disconnect()
      el.removeEventListener("scroll", updateOverflow)
    }
  }, [updateOverflow, children])

  const scrollByOne = (direction: 1 | -1) => {
    const el = scrollerRef.current
    if (!el) return
    const items = Array.from(el.children) as HTMLElement[]
    if (items.length === 0) return
    if (direction === 1) {
      const viewportRight = el.scrollLeft + el.clientWidth
      const target = items.find((item) => item.offsetLeft + item.offsetWidth > viewportRight + 1)
      if (target) {
        el.scrollTo({ left: Math.max(0, target.offsetLeft - 8), behavior: "smooth" })
      } else {
        el.scrollTo({ left: el.scrollWidth, behavior: "smooth" })
      }
    } else {
      const viewportLeft = el.scrollLeft
      const before = items.filter((item) => item.offsetLeft < viewportLeft - 1)
      const target = before[before.length - 1]
      if (target) {
        const next = target.offsetLeft + target.offsetWidth - el.clientWidth + 8
        el.scrollTo({ left: Math.max(0, next), behavior: "smooth" })
      } else {
        el.scrollTo({ left: 0, behavior: "smooth" })
      }
    }
  }

  return (
    <div className={cn("relative min-w-0", className)} data-testid={testId}>
      <div
        ref={scrollerRef}
        className="flex flex-nowrap items-center gap-1.5 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {children}
      </div>
      {canLeft ? (
        <>
          <div
            aria-hidden
            className={cn(
              "pointer-events-none absolute inset-y-0 left-0 w-8 bg-gradient-to-r to-transparent",
              fadeFromClass,
            )}
          />
          <button
            type="button"
            aria-label="Scroll badges left"
            onClick={(event) => {
              event.stopPropagation()
              scrollByOne(-1)
            }}
            className="bg-background/90 text-muted-foreground hover:text-foreground absolute top-1/2 left-0 z-10 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-full border shadow-sm"
          >
            <ChevronLeft className="h-3 w-3" />
          </button>
        </>
      ) : null}
      {canRight ? (
        <>
          <div
            aria-hidden
            className={cn(
              "pointer-events-none absolute inset-y-0 right-0 w-8 bg-gradient-to-l to-transparent",
              fadeFromClass,
            )}
          />
          <button
            type="button"
            aria-label="Scroll badges right"
            onClick={(event) => {
              event.stopPropagation()
              scrollByOne(1)
            }}
            className="bg-background/90 text-muted-foreground hover:text-foreground absolute top-1/2 right-0 z-10 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-full border shadow-sm"
          >
            <ChevronRight className="h-3 w-3" />
          </button>
        </>
      ) : null}
    </div>
  )
}

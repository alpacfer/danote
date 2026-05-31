import { useEffect, useRef, type ReactNode } from "react"

import { TabsList } from "@/components/ui/tabs"

type PinnedTabsListProps = {
  activeTab: string
  ariaLabel: string
  children: ReactNode
}

export function PinnedTabsList({
  activeTab,
  ariaLabel,
  children,
}: PinnedTabsListProps) {
  const scrollerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const activeTrigger = scrollerRef.current?.querySelector<HTMLElement>(
      '[role="tab"][data-state="active"]',
    )
    activeTrigger?.scrollIntoView?.({ behavior: "smooth", block: "nearest", inline: "nearest" })
  }, [activeTab])

  return (
    <div
      ref={scrollerRef}
      role="region"
      aria-label={ariaLabel}
      tabIndex={0}
      className="w-full min-w-0 max-w-full overflow-x-auto overscroll-x-contain pb-1 [scrollbar-width:thin]"
    >
      <TabsList className="min-w-max">
        {children}
      </TabsList>
    </div>
  )
}

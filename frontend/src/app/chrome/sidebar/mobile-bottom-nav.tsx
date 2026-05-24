import { BookOpen, ScrollText, Search, Settings } from "lucide-react"

import type { AppSection } from "@/app/core"
import { cn } from "@/lib/utils"

type MobileBottomNavProps = {
  activeSection: AppSection
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectAccount: () => void
  onOpenSearch: () => void
  unreadWordbankNotificationCount?: number
}

export function MobileBottomNav({
  activeSection,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectAccount,
  onOpenSearch,
  unreadWordbankNotificationCount = 0,
}: MobileBottomNavProps) {
  return (
    <div
      data-slot="mobile-bottom-nav"
      className="fixed bottom-[calc(1.5rem+env(safe-area-inset-bottom))] left-1/2 z-50 flex w-[calc(100%-2rem)] max-w-sm -translate-x-1/2 items-center justify-between gap-3 md:hidden"
    >
      {/* Settings Pill */}
      <button
        type="button"
        aria-label="Settings"
        onClick={onSelectAccount}
        className={cn(
          "flex size-11 shrink-0 items-center justify-center rounded-full border border-border bg-background shadow-lg text-muted-foreground transition-all duration-200 active:scale-90 hover:text-foreground",
          activeSection === "account"
            ? "bg-primary text-primary-foreground border-primary shadow-sm"
            : "hover:bg-muted/60"
        )}
      >
        <Settings className="size-5" />
      </button>

      {/* Main Tabs Pill */}
      <div className="flex h-11 flex-1 items-center justify-between rounded-full border border-border bg-background p-1 shadow-lg">
        {/* Wordbank Tab */}
        <button
          type="button"
          onClick={onSelectWordbank}
          className={cn(
            "relative flex h-9 flex-1 items-center justify-center gap-1.5 rounded-full px-2 text-xs font-semibold transition-all duration-200 active:scale-95 text-muted-foreground hover:text-foreground",
            activeSection === "wordbank"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "hover:bg-muted/60"
          )}
        >
          <BookOpen className="size-5" />
          <span>Wordbank</span>
          {unreadWordbankNotificationCount > 0 && (
            <span
              className={cn(
                "absolute -top-1 -right-1 flex min-w-5 h-5 items-center justify-center rounded-full px-1.5 text-[9px] font-bold leading-none shadow-sm",
                activeSection === "wordbank"
                  ? "bg-destructive text-destructive-foreground"
                  : "bg-primary text-primary-foreground"
              )}
            >
              {unreadWordbankNotificationCount}
            </span>
          )}
        </button>

        {/* Sentencebank Tab */}
        <button
          type="button"
          onClick={onSelectSentencebank}
          className={cn(
            "flex h-9 flex-1 items-center justify-center gap-1.5 rounded-full px-2 text-xs font-semibold transition-all duration-200 active:scale-95 text-muted-foreground hover:text-foreground",
            activeSection === "sentencebank"
              ? "bg-primary text-primary-foreground shadow-sm"
              : "hover:bg-muted/60"
          )}
        >
          <ScrollText className="size-5" />
          <span>Sentences</span>
        </button>
      </div>

      {/* Search Pill */}
      <button
        type="button"
        aria-label="Open search"
        onClick={onOpenSearch}
        className="flex size-11 shrink-0 items-center justify-center rounded-full border border-border bg-background shadow-lg text-muted-foreground transition-all duration-200 active:scale-90 hover:bg-muted/60 hover:text-foreground"
      >
        <Search className="size-5" />
      </button>
    </div>
  )
}

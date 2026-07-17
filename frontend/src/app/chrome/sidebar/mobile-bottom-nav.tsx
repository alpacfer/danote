import { BookOpen, ScrollText, Search, Settings } from "lucide-react"

import type { AppSection } from "@/app/core"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"

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
      <Button
        type="button"
        aria-label="Settings"
        onClick={onSelectAccount}
        variant={activeSection === "account" ? "default" : "outline"}
        size="icon-lg"
        className="size-11 rounded-full shadow-floating"
      >
        <Settings />
      </Button>

      <ButtonGroup className="bg-surface-raised h-11 flex-1 items-center rounded-full border p-1 shadow-floating [&>*]:rounded-full!">
        <Button
          type="button"
          aria-label="Wordbank"
          onClick={onSelectWordbank}
          variant={activeSection === "wordbank" ? "default" : "ghost"}
          size="sm"
          className="relative h-9 flex-1"
        >
          <BookOpen data-icon="inline-start" />
          <span>Words</span>
          {unreadWordbankNotificationCount > 0 && (
            <Badge
              variant={activeSection === "wordbank" ? "destructive" : "default"}
              className="absolute -top-1 -right-1 h-5 min-w-5 px-1 text-[9px] leading-none shadow-xs"
            >
              {unreadWordbankNotificationCount}
            </Badge>
          )}
        </Button>

        <Button
          type="button"
          aria-label="Sentences"
          onClick={onSelectSentencebank}
          variant={activeSection === "sentencebank" ? "default" : "ghost"}
          size="sm"
          className="h-9 flex-1"
        >
          <ScrollText data-icon="inline-start" />
          <span>Sentences</span>
        </Button>
      </ButtonGroup>

      <Button
        type="button"
        aria-label="Open search"
        onClick={onOpenSearch}
        variant="outline"
        size="icon-lg"
        className="size-11 rounded-full shadow-floating"
      >
        <Search />
      </Button>
    </div>
  )
}

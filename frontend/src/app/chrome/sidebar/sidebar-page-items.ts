import { BookOpen, Hash, ScrollText, Settings, type LucideIcon } from "lucide-react"
import { useMemo } from "react"

import { NUMBERS_SENTINEL, danishNumber, numberFromSearchQuery } from "@/app/sections/wordbank/numbers/numbers-data"

export type SidebarPageItem = {
  key: string
  label: string
  shortcut: string
  icon: LucideIcon
  onSelect: () => void
}

export type SidebarNavigationActions = {
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
  onSelectAccount: () => void
  onOpenWordbankLemma: (lemma: string) => void
}

export const SIDEBAR_PAGE_DEFINITIONS = {
  wordbank: { key: "page-wordbank", label: "Words", shortcut: "Alt+W", icon: BookOpen },
  sentencebank: { key: "page-sentencebank", label: "Sentences", shortcut: "Alt+S", icon: ScrollText },
  developer: { key: "page-developer", label: "Developer", shortcut: "Alt+D", icon: Settings },
} satisfies Record<string, Omit<SidebarPageItem, "onSelect">>

export function useSidebarPageItems({
  normalizedQuery,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
}: Omit<SidebarNavigationActions, "onSelectAccount"> & { normalizedQuery: string }) {
  return useMemo(() => {
    const numericQuery = numberFromSearchQuery(normalizedQuery)
    const isDeveloperUnlocked = normalizedQuery === "chochito"
    const pageItems: SidebarPageItem[] = [
      { ...SIDEBAR_PAGE_DEFINITIONS.wordbank, onSelect: onSelectWordbank },
      { ...SIDEBAR_PAGE_DEFINITIONS.sentencebank, onSelect: onSelectSentencebank },
      ...(isDeveloperUnlocked ? [{ ...SIDEBAR_PAGE_DEFINITIONS.developer, onSelect: onSelectDeveloper }] : []),
    ]
    if (numericQuery !== null) {
      return [
        {
          key: "page-numbers",
          label: `${numericQuery} = ${danishNumber(numericQuery)}`,
          shortcut: "Numbers",
          icon: Hash,
          onSelect: () => onOpenWordbankLemma(NUMBERS_SENTINEL),
        },
      ]
    }
    if (!normalizedQuery) {
      return pageItems
    }
    if (isDeveloperUnlocked) {
      return pageItems
    }
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [
    normalizedQuery,
    onOpenWordbankLemma,
    onSelectDeveloper,
    onSelectSentencebank,
    onSelectWordbank,
  ])
}

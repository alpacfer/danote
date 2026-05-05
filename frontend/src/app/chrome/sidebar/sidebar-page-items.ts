import { BookOpen, Hash, Settings, type LucideIcon } from "lucide-react"
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
  onOpenWordbankLemma: (lemma: string) => void
}

export function useSidebarPageItems({
  normalizedQuery,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenWordbankLemma,
}: SidebarNavigationActions & { normalizedQuery: string }) {
  return useMemo(() => {
    const numericQuery = numberFromSearchQuery(normalizedQuery)
    const pageItems: SidebarPageItem[] = [
      { key: "page-wordbank", label: "Wordbank", shortcut: "Alt+W", icon: BookOpen, onSelect: onSelectWordbank },
      { key: "page-sentencebank", label: "Sentencebank", shortcut: "Alt+S", icon: BookOpen, onSelect: onSelectSentencebank },
      { key: "page-developer", label: "Developer", shortcut: "Alt+D", icon: Settings, onSelect: onSelectDeveloper },
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
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [normalizedQuery, onOpenWordbankLemma, onSelectDeveloper, onSelectSentencebank, onSelectWordbank])
}

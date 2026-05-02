import { BookOpen, Settings, type LucideIcon } from "lucide-react"
import { useMemo } from "react"

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
}

export function useSidebarPageItems({
  normalizedQuery,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
}: SidebarNavigationActions & { normalizedQuery: string }) {
  return useMemo(() => {
    const pageItems: SidebarPageItem[] = [
      { key: "page-wordbank", label: "Wordbank", shortcut: "Alt+W", icon: BookOpen, onSelect: onSelectWordbank },
      { key: "page-sentencebank", label: "Sentencebank", shortcut: "Alt+S", icon: BookOpen, onSelect: onSelectSentencebank },
      { key: "page-developer", label: "Developer", shortcut: "Alt+D", icon: Settings, onSelect: onSelectDeveloper },
    ]
    if (!normalizedQuery) {
      return pageItems
    }
    return pageItems.filter((item) => item.label.toLocaleLowerCase("da-DK").includes(normalizedQuery))
  }, [normalizedQuery, onSelectDeveloper, onSelectSentencebank, onSelectWordbank])
}

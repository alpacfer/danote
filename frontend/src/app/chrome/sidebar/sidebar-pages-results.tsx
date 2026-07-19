import { SearchSection } from "@/app/chrome/sidebar/sidebar-search-presentation"
import { CommandItem } from "@/components/ui/command"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import type { SidebarPageItem } from "@/app/chrome/sidebar/sidebar-page-items"

type SidebarPagesResultsProps = {
  matchingPageItems: SidebarPageItem[]
  onCloseSearch: () => void
}

function renderShortcut(shortcut: string) {
  const keys = shortcut.split("+")
  if (keys.length === 1) return <Kbd>{shortcut}</Kbd>
  return (
    <KbdGroup>
      {keys.map((k) => (
        <Kbd key={k}>{k}</Kbd>
      ))}
    </KbdGroup>
  )
}

export function SidebarPagesResults({ matchingPageItems, onCloseSearch }: SidebarPagesResultsProps) {
  if (matchingPageItems.length === 0) return null

  return (
    <SearchSection heading="Go to" material="reference">
      {matchingPageItems.map((item) => {
        const Icon = item.icon
        return (
          <CommandItem
            key={item.key}
            value={item.key}
            data-search-slip
            data-material="reference"
            className="max-md:h-12 max-md:text-base max-md:[&_svg:not([class*='size-'])]:size-5"
            onSelect={() => {
              item.onSelect()
              onCloseSearch()
            }}
          >
            <Icon />
            <span>{item.label}</span>
            <span className="ml-auto hidden md:inline-flex">{renderShortcut(item.shortcut)}</span>
          </CommandItem>
        )
      })}
    </SearchSection>
  )
}

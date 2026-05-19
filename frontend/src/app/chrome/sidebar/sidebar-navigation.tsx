import { Search } from "lucide-react"

import { SIDEBAR_PAGE_DEFINITIONS, type SidebarNavigationActions } from "@/app/chrome/sidebar/sidebar-page-items"
import type { AppSection } from "@/app/core"
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Kbd, KbdGroup } from "@/components/ui/kbd"

type SidebarNavigationProps = Pick<
  SidebarNavigationActions,
  "onSelectWordbank" | "onSelectSentencebank" | "onSelectDeveloper"
> & {
  activeSection: AppSection
  unreadWordbankNotificationCount: number
  onOpenSearch: () => void
}

export function SidebarNavigation({
  activeSection,
  unreadWordbankNotificationCount,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
  onOpenSearch,
}: SidebarNavigationProps) {
  const WordbankIcon = SIDEBAR_PAGE_DEFINITIONS.wordbank.icon
  const SentencebankIcon = SIDEBAR_PAGE_DEFINITIONS.sentencebank.icon
  const DeveloperIcon = SIDEBAR_PAGE_DEFINITIONS.developer.icon

  return (
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" onClick={onOpenSearch} className="max-md:h-12 max-md:text-base max-md:[&>svg]:size-5">
                <Search />
                <span>Search</span>
                <KbdGroup aria-hidden="true" className="ml-auto hidden md:flex">
                  <Kbd>⌘</Kbd>
                  <Kbd>K</Kbd>
                </KbdGroup>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                type="button"
                isActive={activeSection === "wordbank"}
                onClick={onSelectWordbank}
                className="max-md:h-12 max-md:text-base max-md:[&>svg]:size-5"
              >
                <WordbankIcon />
                <span>Wordbank</span>
                {unreadWordbankNotificationCount > 0 ? (
                  <span className="bg-primary text-primary-foreground ml-auto inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] leading-5">
                    {unreadWordbankNotificationCount}
                  </span>
                ) : (
                  <KbdGroup aria-hidden="true" className="ml-auto hidden md:flex">
                    <Kbd>Alt</Kbd>
                    <Kbd>W</Kbd>
                  </KbdGroup>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                type="button"
                isActive={activeSection === "sentencebank"}
                onClick={onSelectSentencebank}
                className="max-md:h-12 max-md:text-base max-md:[&>svg]:size-5"
              >
                <SentencebankIcon />
                <span>Sentencebank</span>
                <KbdGroup aria-hidden="true" className="ml-auto hidden md:flex">
                  <Kbd>Alt</Kbd>
                  <Kbd>S</Kbd>
                </KbdGroup>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                type="button"
                isActive={activeSection === "developer"}
                onClick={onSelectDeveloper}
                className="max-md:h-12 max-md:text-base max-md:[&>svg]:size-5"
              >
                <DeveloperIcon />
                <span>Developer</span>
                <KbdGroup aria-hidden="true" className="ml-auto hidden md:flex">
                  <Kbd>Alt</Kbd>
                  <Kbd>D</Kbd>
                </KbdGroup>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  )
}

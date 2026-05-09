import { BookOpen, Search, Settings, ScrollText } from "lucide-react"

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
import type { SidebarNavigationActions } from "@/app/chrome/sidebar/sidebar-page-items"

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
  return (
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" onClick={onOpenSearch}>
                <Search />
                <span>Search</span>
                <KbdGroup aria-hidden="true" className="ml-auto">
                  <Kbd>⌘</Kbd>
                  <Kbd>K</Kbd>
                </KbdGroup>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" isActive={activeSection === "wordbank"} onClick={onSelectWordbank}>
                <BookOpen />
                <span>Wordbank</span>
                {unreadWordbankNotificationCount > 0 ? (
                  <span className="bg-primary text-primary-foreground ml-auto inline-flex min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] leading-5">
                    {unreadWordbankNotificationCount}
                  </span>
                ) : (
                  <KbdGroup aria-hidden="true" className="ml-auto">
                    <Kbd>Alt</Kbd>
                    <Kbd>W</Kbd>
                  </KbdGroup>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" isActive={activeSection === "sentencebank"} onClick={onSelectSentencebank}>
                <ScrollText />
                <span>Sentencebank</span>
                <KbdGroup aria-hidden="true" className="ml-auto">
                  <Kbd>Alt</Kbd>
                  <Kbd>S</Kbd>
                </KbdGroup>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" isActive={activeSection === "developer"} onClick={onSelectDeveloper}>
                <Settings />
                <span>Developer</span>
                <KbdGroup aria-hidden="true" className="ml-auto">
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

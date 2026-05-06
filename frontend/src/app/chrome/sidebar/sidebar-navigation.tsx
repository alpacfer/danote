import { BookOpen, Settings } from "lucide-react"

import type { AppSection } from "@/app/core"
import {
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { Kbd, KbdGroup } from "@/components/ui/kbd"
import type { SidebarNavigationActions } from "@/app/chrome/sidebar/sidebar-page-items"

type SidebarNavigationProps = SidebarNavigationActions & {
  activeSection: AppSection
  unreadWordbankNotificationCount: number
}

export function SidebarNavigation({
  activeSection,
  unreadWordbankNotificationCount,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
}: SidebarNavigationProps) {
  return (
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>Navigation</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
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
                <BookOpen />
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

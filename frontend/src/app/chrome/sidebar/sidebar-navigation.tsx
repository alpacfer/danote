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
import type { SidebarNavigationActions } from "@/app/chrome/sidebar/sidebar-page-items"

type SidebarNavigationProps = SidebarNavigationActions & {
  activeSection: AppSection
  unreadWordbankNotificationCount: number
}

export function SidebarNavigation({
  activeSection,
  unreadWordbankNotificationCount,
  onSelectNotes,
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
              <SidebarMenuButton type="button" isActive={activeSection === "notes"} onClick={onSelectNotes}>
                <BookOpen />
                <span>Notes</span>
                <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+N</span>
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
                  <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+W</span>
                )}
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" isActive={activeSection === "sentencebank"} onClick={onSelectSentencebank}>
                <BookOpen />
                <span>Sentencebank</span>
                <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+S</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton type="button" isActive={activeSection === "developer"} onClick={onSelectDeveloper}>
                <Settings />
                <span>Developer</span>
                <span aria-hidden="true" className="text-muted-foreground ml-auto text-[11px]">Alt+D</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
  )
}

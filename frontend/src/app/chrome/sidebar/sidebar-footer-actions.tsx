import { UserCircle } from "lucide-react"

import { ThemeToggleButton } from "@/app/chrome/theme-toggle-button"
import type { AppSection } from "@/app/core"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type SidebarFooterActionsProps = {
  activeSection: AppSection
  onSelectAccount: () => void
}

export function SidebarFooterActions({ activeSection, onSelectAccount }: SidebarFooterActionsProps) {
  return (
    <div className="flex items-center gap-1 group-data-[collapsible=icon]:flex-col group-data-[collapsible=icon]:items-start group-data-[collapsible=icon]:justify-center">
      <Button
        type="button"
        variant="ghost"
        size="icon-sm"
        aria-label="Open account"
        aria-current={activeSection === "account" ? "page" : undefined}
        className={cn(
          "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground max-md:size-10 max-md:[&_svg:not([class*='size-'])]:size-5",
          activeSection === "account" && "bg-sidebar-accent text-sidebar-accent-foreground",
        )}
        onClick={onSelectAccount}
      >
        <UserCircle />
      </Button>
      <ThemeToggleButton />
    </div>
  )
}

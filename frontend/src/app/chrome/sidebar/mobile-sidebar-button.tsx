import { PanelLeft } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useIsMobile } from "@/hooks/use-mobile"
import { useSidebar } from "@/components/ui/vendor/sidebar"

export function MobileSidebarButton() {
  const isMobile = useIsMobile()
  const { openMobile, setOpenMobile } = useSidebar()

  if (!isMobile) return null

  return (
    <Button
      type="button"
      size="icon"
      aria-label="Toggle sidebar"
      className="fixed left-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-40 size-14 rounded-full shadow-lg md:hidden [&>svg]:size-6"
      onClick={() => setOpenMobile(!openMobile)}
    >
      <PanelLeft />
    </Button>
  )
}

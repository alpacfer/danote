import { Search } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useIsMobile } from "@/hooks/use-mobile"

type MobileSearchButtonProps = {
  isSearchOpen: boolean
  onOpenSearch: () => void
}

export function MobileSearchButton({ isSearchOpen, onOpenSearch }: MobileSearchButtonProps) {
  const isMobile = useIsMobile()

  if (!isMobile || isSearchOpen) {
    return null
  }

  return (
    <Button
      type="button"
      size="icon"
      aria-label="Open search"
      className="fixed right-4 bottom-[calc(1rem+env(safe-area-inset-bottom))] z-40 size-14 rounded-full shadow-lg md:hidden [&>svg]:size-6"
      onClick={onOpenSearch}
    >
      <Search />
    </Button>
  )
}

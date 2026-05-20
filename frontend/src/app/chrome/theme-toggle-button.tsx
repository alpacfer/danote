import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

export function ThemeToggleButton() {
  const { resolvedTheme, setTheme } = useTheme()
  const isDark = resolvedTheme === "dark"

  return (
    <Button
      type="button"
      variant="ghost"
      size="icon-sm"
      className="text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground size-12 md:size-8 [&_svg:not([class*='size-'])]:size-5 md:[&_svg:not([class*='size-'])]:size-4"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => {
        setTheme(isDark ? "light" : "dark")
      }}
    >
      {isDark ? <Sun /> : <Moon />}
    </Button>
  )
}

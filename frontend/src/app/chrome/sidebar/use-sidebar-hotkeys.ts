import { useEffect } from "react"

type UseSidebarHotkeysParams = {
  onToggleSearch: () => void
  onSelectWordbank: () => void
  onSelectSentencebank: () => void
  onSelectDeveloper: () => void
}

export function useSidebarHotkeys({
  onToggleSearch,
  onSelectWordbank,
  onSelectSentencebank,
  onSelectDeveloper,
}: UseSidebarHotkeysParams) {
  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      const key = event.key.toLowerCase()
      const shouldOpenSearch = (event.metaKey || event.ctrlKey) && key === "k"
      if (shouldOpenSearch) {
        event.preventDefault()
        onToggleSearch()
        return
      }

      const target = event.target as HTMLElement | null
      const isTypingTarget = Boolean(
        target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable),
      )
      if (isTypingTarget || !event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
        return
      }

      if (key === "w") {
        event.preventDefault()
        onSelectWordbank()
        return
      }
      if (key === "s") {
        event.preventDefault()
        onSelectSentencebank()
        return
      }
      if (key === "d") {
        event.preventDefault()
        onSelectDeveloper()
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => {
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [onSelectDeveloper, onSelectSentencebank, onSelectWordbank, onToggleSearch])
}

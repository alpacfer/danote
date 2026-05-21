import { useCallback, useEffect } from "react"

const SEARCH_HISTORY_KEY = "danote.search"

type UseSidebarSearchHistoryParams = {
  isSearchOpen: boolean
  onCloseFromHistory: () => void
}

function currentBrowserState(): Record<string, unknown> {
  return ((window.history.state as Record<string, unknown> | null) ?? {})
}

function isSearchHistoryState(): boolean {
  if (typeof window === "undefined") return false
  return Boolean(currentBrowserState()[SEARCH_HISTORY_KEY])
}

export function useSidebarSearchHistory({
  isSearchOpen,
  onCloseFromHistory,
}: UseSidebarSearchHistoryParams) {
  const push = useCallback(() => {
    if (typeof window === "undefined" || isSearchHistoryState()) return
    window.history.pushState({ ...currentBrowserState(), [SEARCH_HISTORY_KEY]: true }, "")
  }, [])

  const clear = useCallback(() => {
    if (typeof window === "undefined" || !isSearchHistoryState()) return
    const nextState = { ...currentBrowserState() }
    delete nextState[SEARCH_HISTORY_KEY]
    window.history.replaceState(nextState, "")
  }, [])

  useEffect(() => {
    function handlePopState() {
      if (!isSearchOpen || isSearchHistoryState()) return
      onCloseFromHistory()
    }

    window.addEventListener("popstate", handlePopState)
    return () => window.removeEventListener("popstate", handlePopState)
  }, [isSearchOpen, onCloseFromHistory])

  return { clear, push }
}

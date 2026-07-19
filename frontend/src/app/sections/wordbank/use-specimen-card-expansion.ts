import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FocusEvent,
  type KeyboardEvent,
  type PointerEvent,
} from "react"

type ExpansionDirection = "down" | "up"
type ExpansionAlignment = "end" | "start"

type UseSpecimenCardExpansionOptions = {
  enabled: boolean
  open: boolean
  onOpenChange: (open: boolean) => void
}

const CARD_HEIGHT = 32
const EXPANDED_WIDTH = 320
const VIEWPORT_MARGIN = 16
const OPEN_DELAY = 70
const CLOSE_DELAY = 120

export function useSpecimenCardExpansion({
  enabled,
  open,
  onOpenChange,
}: UseSpecimenCardExpansionOptions) {
  const anchorRef = useRef<HTMLDivElement>(null)
  const surfaceRef = useRef<HTMLDivElement>(null)
  const previewRef = useRef<HTMLDivElement>(null)
  const openTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const closeTimerRef = useRef<ReturnType<typeof window.setTimeout> | null>(null)
  const [direction, setDirection] = useState<ExpansionDirection>("down")
  const [alignment, setAlignment] = useState<ExpansionAlignment>("start")

  const clearTimers = useCallback(() => {
    if (openTimerRef.current !== null) window.clearTimeout(openTimerRef.current)
    if (closeTimerRef.current !== null) window.clearTimeout(closeTimerRef.current)
    openTimerRef.current = null
    closeTimerRef.current = null
  }, [])

  const updatePlacement = useCallback(() => {
    const anchor = anchorRef.current
    const surface = surfaceRef.current
    const preview = previewRef.current
    if (!anchor || !surface || !preview) return

    const viewport = window.visualViewport
    const viewportLeft = viewport?.offsetLeft ?? 0
    const viewportTop = viewport?.offsetTop ?? 0
    const viewportWidth = viewport?.width ?? window.innerWidth
    const viewportHeight = viewport?.height ?? window.innerHeight
    const anchorRect = anchor.getBoundingClientRect()
    const availableWidth = Math.max(0, viewportWidth - VIEWPORT_MARGIN * 2)
    const expandedWidth = Math.max(
      anchorRect.width,
      Math.min(EXPANDED_WIDTH, availableWidth),
    )

    surface.style.setProperty("--wordbank-card-expanded-width", `${expandedWidth}px`)
    preview.style.width = `${expandedWidth}px`

    const previewHeight = preview.scrollHeight
    const expandedHeight = Math.max(CARD_HEIGHT, previewHeight)
    const viewportBottom = viewportTop + viewportHeight
    const viewportRight = viewportLeft + viewportWidth
    const roomBelow = viewportBottom - VIEWPORT_MARGIN - anchorRect.bottom
    const roomAbove = anchorRect.top - viewportTop - VIEWPORT_MARGIN
    const nextDirection = roomBelow >= previewHeight || roomBelow >= roomAbove
      ? "down"
      : "up"
    const nextAlignment = anchorRect.left + expandedWidth <= viewportRight - VIEWPORT_MARGIN
      ? "start"
      : "end"

    surface.style.setProperty("--wordbank-card-expanded-height", `${expandedHeight}px`)
    anchor.style.setProperty("--wordbank-card-expanded-height", `${expandedHeight}px`)
    anchor.style.setProperty("--wordbank-card-expanded-width", `${expandedWidth}px`)
    anchor.style.setProperty(
      "--wordbank-card-inline-shift",
      nextAlignment === "end" ? `${anchorRect.width - expandedWidth}px` : "0px",
    )
    setDirection(nextDirection)
    setAlignment(nextAlignment)
  }, [])

  const openImmediately = useCallback(() => {
    if (!enabled) return
    clearTimers()
    updatePlacement()
    onOpenChange(true)
  }, [clearTimers, enabled, onOpenChange, updatePlacement])

  const scheduleOpen = useCallback(() => {
    if (!enabled || open) return
    clearTimers()
    openTimerRef.current = window.setTimeout(openImmediately, OPEN_DELAY)
  }, [clearTimers, enabled, open, openImmediately])

  const scheduleClose = useCallback(() => {
    clearTimers()
    if (!open) return
    closeTimerRef.current = window.setTimeout(() => {
      onOpenChange(false)
      closeTimerRef.current = null
    }, CLOSE_DELAY)
  }, [clearTimers, onOpenChange, open])

  const dismiss = useCallback(() => {
    clearTimers()
    onOpenChange(false)
  }, [clearTimers, onOpenChange])

  useEffect(() => clearTimers, [clearTimers])

  useEffect(() => {
    if (!open) return
    const frameId = window.requestAnimationFrame(updatePlacement)
    const handleViewportChange = () => updatePlacement()
    window.addEventListener("resize", handleViewportChange)
    window.addEventListener("scroll", handleViewportChange, true)
    window.visualViewport?.addEventListener("resize", handleViewportChange)
    window.visualViewport?.addEventListener("scroll", handleViewportChange)
    return () => {
      window.cancelAnimationFrame(frameId)
      window.removeEventListener("resize", handleViewportChange)
      window.removeEventListener("scroll", handleViewportChange, true)
      window.visualViewport?.removeEventListener("resize", handleViewportChange)
      window.visualViewport?.removeEventListener("scroll", handleViewportChange)
    }
  }, [open, updatePlacement])

  return {
    alignment,
    anchorRef,
    direction,
    previewRef,
    surfaceRef,
    onBlur(event: FocusEvent<HTMLButtonElement>) {
      if (anchorRef.current?.contains(event.relatedTarget)) return
      scheduleClose()
    },
    onFocus: openImmediately,
    onKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
      if (event.key !== "Escape" || !open) return
      event.preventDefault()
      event.stopPropagation()
      dismiss()
    },
    onPointerDown(event: PointerEvent<HTMLButtonElement>) {
      if (event.pointerType !== "touch") return
      dismiss()
    },
    onPointerEnter(event: PointerEvent<HTMLButtonElement>) {
      if (event.pointerType === "touch") return
      if (closeTimerRef.current !== null) {
        window.clearTimeout(closeTimerRef.current)
        closeTimerRef.current = null
      }
      scheduleOpen()
    },
    onPointerLeave(event: PointerEvent<HTMLButtonElement>) {
      if (event.pointerType === "touch") return
      scheduleClose()
    },
  }
}

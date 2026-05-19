import * as React from "react"

const VISUAL_VH_VAR = "--app-visual-vh"
const KEYBOARD_INSET_VAR = "--app-keyboard-inset"

/**
 * While `enabled`, mirrors the visual viewport into CSS custom properties on
 * `<html>` so the search dialog can sit above the on-screen keyboard:
 *
 * - `--app-visual-vh`: visible viewport height in px (shrinks with the keyboard).
 * - `--app-keyboard-inset`: px hidden behind the keyboard at the bottom.
 *
 * Both properties are removed when disabled/unmounted, so consumers fall back to
 * their static defaults (100dvh / 0px) whenever search is closed.
 */
export function useVisualViewportVars(enabled: boolean) {
  React.useEffect(() => {
    const viewport = window.visualViewport
    if (!enabled || !viewport) {
      return
    }

    const root = document.documentElement
    let frame = 0
    let lastVh = -1
    let lastInset = -1
    // iOS reports fractional, fluctuating visualViewport metrics (resizes-visual);
    // Android resizes the layout viewport (resizes-content) and reports integers.
    // Round to whole px and skip no-op writes so both platforms stay jitter-free.
    const sync = () => {
      frame = 0
      const vh = Math.round(viewport.height)
      const inset = Math.max(
        0,
        Math.round(window.innerHeight - viewport.height - viewport.offsetTop),
      )
      if (vh !== lastVh) {
        lastVh = vh
        root.style.setProperty(VISUAL_VH_VAR, `${vh}px`)
      }
      if (inset !== lastInset) {
        lastInset = inset
        root.style.setProperty(KEYBOARD_INSET_VAR, `${inset}px`)
      }
    }
    // Coalesce bursts of resize/scroll (iOS fires many per keyboard frame)
    // into one write per frame so the panel tracks the keyboard without thrash.
    const scheduleSync = () => {
      if (frame === 0) {
        frame = window.requestAnimationFrame(sync)
      }
    }

    sync()
    viewport.addEventListener("resize", scheduleSync)
    viewport.addEventListener("scroll", scheduleSync)
    return () => {
      if (frame !== 0) {
        window.cancelAnimationFrame(frame)
      }
      viewport.removeEventListener("resize", scheduleSync)
      viewport.removeEventListener("scroll", scheduleSync)
      root.style.removeProperty(VISUAL_VH_VAR)
      root.style.removeProperty(KEYBOARD_INSET_VAR)
    }
  }, [enabled])
}

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
    const sync = () => {
      const keyboardInset = Math.max(
        0,
        window.innerHeight - viewport.height - viewport.offsetTop,
      )
      root.style.setProperty(VISUAL_VH_VAR, `${viewport.height}px`)
      root.style.setProperty(KEYBOARD_INSET_VAR, `${keyboardInset}px`)
    }

    sync()
    viewport.addEventListener("resize", sync)
    viewport.addEventListener("scroll", sync)
    return () => {
      viewport.removeEventListener("resize", sync)
      viewport.removeEventListener("scroll", sync)
      root.style.removeProperty(VISUAL_VH_VAR)
      root.style.removeProperty(KEYBOARD_INSET_VAR)
    }
  }, [enabled])
}

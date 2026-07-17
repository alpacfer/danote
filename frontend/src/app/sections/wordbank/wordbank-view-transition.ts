export function wordViewTransitionName(lemma: string): string {
  const safeLemma = lemma
    .normalize("NFKD")
    .toLocaleLowerCase("da-DK")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
  return `danote-word-${safeLemma || "entry"}`
}

export function runWordViewTransition(action: () => void): void {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches
  const transitionDocument = document as Document & {
    startViewTransition?: (callback: () => void) => { finished: Promise<void> }
  }
  if (prefersReducedMotion || !transitionDocument.startViewTransition) {
    action()
    return
  }
  transitionDocument.startViewTransition(action)
}

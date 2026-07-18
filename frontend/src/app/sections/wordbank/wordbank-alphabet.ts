import { useEffect, useState, type RefObject } from "react"

export function useActiveCatalogueLetter(
  containerRef: RefObject<HTMLElement | null>,
  letters: readonly string[],
) {
  const [observedLetter, setObservedLetter] = useState<string | null>(null)
  const lettersKey = letters.join("|")
  const activeLetter = observedLetter && letters.includes(observedLetter)
    ? observedLetter
    : (letters[0] ?? null)

  useEffect(() => {
    const container = containerRef.current
    if (!container || typeof window.IntersectionObserver === "undefined") return

    const scrollRoot = container.closest(".danote-notebook-viewport")
    const observer = new window.IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top)
        const nextLetter = (visible[0]?.target as HTMLElement | undefined)?.dataset.wordbankLetter
        if (nextLetter) setObservedLetter(nextLetter)
      },
      {
        root: scrollRoot,
        rootMargin: "-48px 0px -65% 0px",
        threshold: 0,
      },
    )

    for (const group of container.querySelectorAll<HTMLElement>("[data-wordbank-letter]")) {
      observer.observe(group)
    }
    return () => observer.disconnect()
  }, [containerRef, lettersKey])

  return [activeLetter, setObservedLetter] as const
}

export function catalogueGroupId(letter: string) {
  return `wordbank-letter-${letter.toLocaleLowerCase("da-DK")}`
}

import { act, renderHook } from "@testing-library/react"
import { describe, expect, it } from "vitest"

import { useSectionNavigation } from "@/app/hooks/app/use-section-navigation"

describe("useSectionNavigation history", () => {
  it("syncs browser popstate to internal index", async () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openSentence(11)
    })
    act(() => {
      result.current.openWordbankLemma("hund")
    })
    expect(result.current.selectedLemma).toBe("hund")

    await act(async () => {
      window.history.back()
      await new Promise(resolve => setTimeout(resolve, 50))
    })
    expect(result.current.selectedSentenceId).toBe(11)
    expect(result.current.canGoForward).toBe(true)

    await act(async () => {
      window.history.forward()
      await new Promise(resolve => setTimeout(resolve, 50))
    })
    expect(result.current.selectedLemma).toBe("hund")
  })


  it("starts at the wordbank root with no back/forward", () => {
    const { result } = renderHook(() => useSectionNavigation())

    expect(result.current.activeSection).toBe("wordbank")
    expect(result.current.selectedLemma).toBeNull()
    expect(result.current.canGoBack).toBe(false)
    expect(result.current.canGoForward).toBe(false)
  })

  it("pushes entries on open* and supports back/forward", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openSentence(7)
    })
    expect(result.current.activeSection).toBe("sentencebank")
    expect(result.current.selectedSentenceId).toBe(7)
    expect(result.current.canGoBack).toBe(true)
    expect(result.current.canGoForward).toBe(false)
    expect(result.current.previousEntry?.section).toBe("wordbank")

    act(() => {
      result.current.openWordbankLemma("hund")
    })
    expect(result.current.selectedLemma).toBe("hund")
    expect(result.current.previousEntry?.selectedSentenceId).toBe(7)

    act(() => {
      result.current.goBack()
    })
    expect(result.current.activeSection).toBe("sentencebank")
    expect(result.current.selectedSentenceId).toBe(7)
    expect(result.current.canGoForward).toBe(true)
    expect(result.current.nextEntry?.selectedLemma).toBe("hund")

    act(() => {
      result.current.goForward()
    })
    expect(result.current.selectedLemma).toBe("hund")
  })

  it("truncates forward history when a new entry is pushed mid-history", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openSentence(1)
    })
    act(() => {
      result.current.openWordbankLemma("kat")
    })
    act(() => {
      result.current.goBack()
    })
    expect(result.current.canGoForward).toBe(true)

    act(() => {
      result.current.openSentence(2)
    })
    expect(result.current.canGoForward).toBe(false)
    expect(result.current.selectedSentenceId).toBe(2)
  })

  it("de-duplicates identical pushes", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openSentence(5)
    })
    const indexAfterFirst = result.current.canGoBack
    act(() => {
      result.current.openSentence(5)
    })
    expect(result.current.canGoBack).toBe(indexAfterFirst)
    act(() => {
      result.current.goBack()
    })
    expect(result.current.activeSection).toBe("wordbank")
    expect(result.current.canGoForward).toBe(true)
  })

  it("replaceCurrentSentence swaps the current entry instead of pushing", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openWordbankLemma("hund")
    })
    act(() => {
      result.current.openPendingSentence("Hvor bor du?", "Where do you live?")
    })
    expect(result.current.pendingSentence?.source_text).toBe("Hvor bor du?")

    act(() => {
      result.current.replaceCurrentSentence(99)
    })
    expect(result.current.pendingSentence).toBeNull()
    expect(result.current.selectedSentenceId).toBe(99)

    act(() => {
      result.current.goBack()
    })
    expect(result.current.selectedLemma).toBe("hund")
    expect(result.current.pendingSentence).toBeNull()
  })

  it("openWordbankTarget pushes a single entry for combined lemma+meaning navigation", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openWordbankTarget("hund", 42)
    })
    expect(result.current.selectedLemma).toBe("hund")
    expect(result.current.selectedMeaningId).toBe(42)

    act(() => {
      result.current.goBack()
    })
    expect(result.current.selectedLemma).toBeNull()
    expect(result.current.selectedMeaningId).toBeNull()
  })

  it("raw wordbank meaning navigation keeps built-in lemmas on word pages", () => {
    const { result } = renderHook(() => useSectionNavigation())

    act(() => {
      result.current.openWordbankMeaningRaw("du", 42)
    })

    expect(result.current.selectedLemma).toBe("du")
    expect(result.current.selectedMeaningId).toBe(42)
  })

  it("restores filters on goBack to clear filters at wordbank root", () => {
    const { result } = renderHook(() => useSectionNavigation())

    // 1. Initial State A: wordbank root (no filter)
    expect(result.current.selectedLemma).toBeNull()
    expect(result.current.filters).toEqual({ posTags: [], categories: [] })

    // 2. Go into a word (State B)
    act(() => {
      result.current.openWordbankLemma("se ud")
    })
    expect(result.current.selectedLemma).toBe("se ud")
    expect(result.current.filters).toEqual({ posTags: [], categories: [] })

    // 3. Click on a filter badge: sets filter and navigates back (State C)
    act(() => {
      result.current.applyFilterAndNavigateBack({ posTags: ["PHRASAL_VERB"], categories: [] })
    })
    expect(result.current.selectedLemma).toBeNull()
    expect(result.current.filters).toEqual({ posTags: ["PHRASAL_VERB"], categories: [] })

    // 4. Hit browser back once: should go back to State B (lemma details, clear filters)
    act(() => {
      result.current.goBack()
    })
    expect(result.current.selectedLemma).toBe("se ud")
    expect(result.current.filters).toEqual({ posTags: [], categories: [] })

    // 5. Hit browser back again: should go back to State A (clear list view, clear filters)
    act(() => {
      result.current.goBack()
    })
    expect(result.current.selectedLemma).toBeNull()
    expect(result.current.filters).toEqual({ posTags: [], categories: [] })
  })
})

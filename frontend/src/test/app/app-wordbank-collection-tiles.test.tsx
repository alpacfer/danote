import { act, fireEvent, mockFetchImplementation, renderApp, screen, waitFor, within } from "@/test/app-test-helpers"
import { vi } from "vitest"

describe("App wordbank collection tiles", () => {
  it("renders compact specimen labels and exposes metadata on keyboard focus", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 3,
            pos_tags: ["NOUN"],
            categories: ["School"],
          },
          {
            lemma: "passe på",
            english_translation: "watch out",
            variation_count: 1,
            pos_tags: ["VERB"],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const bogTile = await screen.findByRole("button", { name: "bog" })
    expect(bogTile).toHaveTextContent("bog· 3")
    expect(bogTile.querySelector("svg")).not.toBeInTheDocument()
    expect(bogTile).toHaveAttribute("data-material", "word")
    expect(bogTile).toHaveAttribute("data-grid-anchor", "unit")

    fireEvent.focus(bogTile)
    const tooltip = await screen.findByRole("tooltip")
    expect(within(tooltip).getByText("book")).toBeInTheDocument()
    expect(within(tooltip).getByText("Noun")).toBeInTheDocument()
    expect(within(tooltip).queryByText("Pronunciation available")).not.toBeInTheDocument()

    const mweTile = screen.getByRole("button", { name: "passe på" })
    expect(mweTile).toHaveAttribute("data-mwe", "true")
  })

  it("keeps whole-lemma deletion on the specimen context menu", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            variation_count: 1,
            pos_tags: [],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.contextMenu(await screen.findByRole("button", { name: "bog" }))
    expect(await screen.findByRole("menuitem", { name: /delete whole lemma/i })).toBeInTheDocument()
  })

  it("marks only activity from the last seven days as recent", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
    vi.setSystemTime(new Date("2026-07-17T12:00:00Z"))
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: ["School"],
            created_at: "2026-06-01 08:00:00",
            last_enriched_at: "2026-07-14T08:00:00+00:00",
          },
          {
            lemma: "gammel",
            variation_count: 1,
            pos_tags: ["ADJ"],
            categories: [],
            created_at: "2026-05-01 08:00:00",
            last_enriched_at: "2026-07-01 08:00:00",
          },
        ],
      },
    })

    renderApp()
    expect(await screen.findByLabelText("Recently enriched bog")).toBeInTheDocument()
    expect(screen.queryByLabelText("Recently enriched gammel")).not.toBeInTheDocument()
    vi.useRealTimers()
  })

  it("renders all five references as a distinct deck shelf", async () => {
    mockFetchImplementation({ lemmasResponse: { items: [] } })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(await screen.findByRole("heading", { name: "Reference collections" })).toBeInTheDocument()
    expect(document.querySelector("[data-reference-drawer]")).toHaveClass("grid-cols-2", "md:grid-cols-5")
    const labels = ["Pronouns", "HV Questions", "Prepositions", "Conjunctions", "Numbers & Time"]
    const tones = new Set<string>()
    for (const label of labels) {
      const deck = screen.getByRole("button", { name: `Open ${label} reference` })
      const material = deck.closest<HTMLElement>("[data-material='reference']")
      expect(material).toBeInTheDocument()
      expect(deck.parentElement).toHaveClass("h-full")
      tones.add(material?.dataset.materialTone ?? "")
    }
    expect(tones.size).toBe(5)

    fireEvent.click(screen.getByRole("button", { name: "Open Numbers & Time reference" }))
    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Numbers & Time" })).toBeInTheDocument()
    })
  })

  it("orders Danish catalogue groups and renders a reduced alphabet index", async () => {
    const scrollSpy = vi.spyOn(HTMLElement.prototype, "scrollIntoView")
    mockFetchImplementation({
      lemmasResponse: {
        items: ["ål", "ørn", "æble", "fisk"].map((lemma) => ({
          lemma,
          variation_count: 1,
          pos_tags: ["NOUN"],
          categories: [],
        })),
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const groupLetters = Array.from(document.querySelectorAll<HTMLElement>("[data-wordbank-letter]"))
      .map((group) => group.dataset.wordbankLetter)
    expect(groupLetters).toEqual(["F", "Æ", "Ø", "Å"])
    expect(screen.queryByRole("button", { name: "Jump to A" })).not.toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Jump to Æ" })).toBeEnabled()
    expect(screen.getByRole("button", { name: "Jump to F" })).toHaveAttribute("aria-current", "true")
    const fGroup = document.querySelector<HTMLElement>("[data-wordbank-letter='F']")
    expect(within(fGroup!).getByRole("heading", { name: "F" })).toHaveTextContent(/^F$/)

    fireEvent.click(screen.getByRole("button", { name: "Jump to Å" }))
    expect(scrollSpy).toHaveBeenCalledWith({ behavior: "smooth", block: "start" })
    expect(screen.getByRole("button", { name: "Jump to Å" })).toHaveAttribute("aria-current", "true")
    scrollSpy.mockRestore()
  })

  it("tracks the visible catalogue group through IntersectionObserver", async () => {
    let observerCallback: IntersectionObserverCallback | null = null
    const observe = vi.fn()
    const disconnect = vi.fn()
    class IntersectionObserverMock {
      constructor(callback: IntersectionObserverCallback) {
        observerCallback = callback
      }
      observe = observe
      disconnect = disconnect
      unobserve = vi.fn()
      takeRecords = () => []
      root = null
      rootMargin = ""
      thresholds = []
    }
    vi.stubGlobal("IntersectionObserver", IntersectionObserverMock)
    mockFetchImplementation({
      lemmasResponse: {
        items: ["fisk", "ørn"].map((lemma) => ({
          lemma,
          variation_count: 1,
          pos_tags: ["NOUN"],
          categories: [],
        })),
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    const group = document.querySelector<HTMLElement>("[data-wordbank-letter='Ø']")
    expect(group).not.toBeNull()
    expect(observe).toHaveBeenCalled()

    act(() => {
      observerCallback?.(
        [{
          isIntersecting: true,
          intersectionRatio: 1,
          intersectionRect: { top: 48 } as DOMRectReadOnly,
          boundingClientRect: { top: 48 } as DOMRectReadOnly,
          rootBounds: null,
          target: group!,
          time: 0,
        } as IntersectionObserverEntry],
        {} as IntersectionObserver,
      )
    })
    expect(screen.getByRole("button", { name: "Jump to Ø" })).toHaveAttribute("aria-current", "true")
    vi.unstubAllGlobals()
  })
})

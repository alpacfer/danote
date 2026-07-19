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
            translation_groups: [
              {
                english_translation: "book",
                additional_translations: ["volume", "Book"],
              },
              {
                english_translation: "beech tree",
                additional_translations: [],
              },
            ],
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
    expect(bogTile).toHaveTextContent(/^bog$/)
    expect(bogTile.querySelector("svg")).not.toBeInTheDocument()
    const bogCard = bogTile.closest<HTMLElement>("[data-wordbank-expandable-card]")
    const bogSurface = bogCard?.querySelector("[data-wordbank-expansion-surface]")
    expect(bogSurface).toHaveAttribute("data-material", "word")
    expect(bogSurface).toHaveAttribute("data-index-stock")
    expect(bogSurface).toHaveAttribute("data-paper-stock")
    expect(bogCard).toHaveAttribute("data-grid-anchor", "unit")
    expect(bogCard).toHaveAttribute("data-state", "closed")

    fireEvent.focus(bogTile)
    await waitFor(() => {
      expect(bogCard).toHaveAttribute("data-state", "open")
    })
    const preview = bogCard?.querySelector<HTMLElement>("[data-wordbank-specimen-preview]")
    expect(preview?.closest("[data-index-stock]")).toBeInTheDocument()
    expect(preview?.closest("[data-wordbank-expansion-surface]")).toBeInTheDocument()
    expect(preview?.closest("[data-paper-reveal]")).not.toBeInTheDocument()
    expect(within(preview!).queryByText("bog")).not.toBeInTheDocument()
    expect(within(bogCard!).getByText("bog")).toBeInTheDocument()
    expect(within(preview!).getByText("book")).toBeInTheDocument()
    expect(within(preview!).getByText("volume")).toBeInTheDocument()
    expect(within(preview!).getByText("beech tree")).toBeInTheDocument()
    expect(within(preview!).getByText("Noun")).toBeInTheDocument()
    expect(within(preview!).queryByText("Book")).not.toBeInTheDocument()
    expect(within(preview!).queryByText(/specimen|pronunciation|school|forms/i)).not.toBeInTheDocument()

    expect(bogTile).toHaveAttribute("aria-description", "Noun. book. volume. beech tree")

    const mweTile = screen.getByRole("button", { name: "passe på" })
    expect(mweTile).toHaveAttribute("data-mwe", "true")
  })

  it("uses brief hover intent without changing the card footprint", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    const tile = await screen.findByRole("button", { name: "bog" })
    const card = tile.closest<HTMLElement>("[data-wordbank-expandable-card]")!

    fireEvent.pointerEnter(card, { pointerType: "mouse" })
    expect(card).toHaveAttribute("data-state", "closed")
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 85))
    })
    expect(card).toHaveAttribute("data-state", "open")

    fireEvent.pointerLeave(card, { pointerType: "mouse" })
    expect(card).toHaveAttribute("data-state", "open")
    await act(async () => {
      await new Promise((resolve) => window.setTimeout(resolve, 135))
    })
    expect(card).toHaveAttribute("data-state", "closed")
  })

  it("keeps POS-only previews and omits empty previews", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "gammel",
            variation_count: 1,
            pos_tags: ["ADJ"],
            categories: [],
          },
          {
            lemma: "ukendt",
            variation_count: 1,
            pos_tags: [],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const adjectiveTile = await screen.findByRole("button", { name: "gammel" })
    const adjectiveCard = adjectiveTile.closest<HTMLElement>("[data-wordbank-expandable-card]")
    fireEvent.focus(adjectiveTile)
    await waitFor(() => {
      expect(adjectiveCard).toHaveAttribute("data-state", "open")
    })
    expect(adjectiveCard?.querySelector("[data-wordbank-specimen-preview]"))
      .toHaveTextContent("Adjective")

    fireEvent.blur(adjectiveTile)
    const unknownTile = screen.getByRole("button", { name: "ukendt" })
    const unknownCard = unknownTile.closest<HTMLElement>("[data-wordbank-expandable-card]")
    fireEvent.focus(unknownTile)
    await waitFor(() => {
      expect(adjectiveCard).toHaveAttribute("data-state", "closed")
    })
    expect(unknownCard?.querySelector("[data-wordbank-specimen-preview]")).not.toBeInTheDocument()
    expect(unknownCard).toHaveAttribute("data-state", "closed")
    expect(unknownTile).not.toHaveAttribute("aria-description")
  })

  it("dismisses the preview with Escape without changing the selected word", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: [],
          },
        ],
      },
    })

    renderApp()
    const tile = await screen.findByRole("button", { name: "bog" })
    const card = tile.closest<HTMLElement>("[data-wordbank-expandable-card]")
    await act(async () => {
      tile.focus()
    })
    await waitFor(() => {
      expect(card).toHaveAttribute("data-state", "open")
    })

    await act(async () => {
      fireEvent.keyDown(tile, { key: "Escape" })
    })
    await waitFor(() => {
      expect(card).toHaveAttribute("data-state", "closed")
    })
    expect(tile).toHaveFocus()
    expect(screen.queryByRole("heading", { name: "bog" })).not.toBeInTheDocument()
  })

  it("keeps touch interaction as one-tap word-page navigation", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: [],
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        is_sectioned: false,
        pos_tag: "NOUN",
        surface_forms: [],
      },
    })

    renderApp()
    const tile = await screen.findByRole("button", { name: "bog" })
    fireEvent.pointerDown(tile, { pointerType: "touch" })
    expect(tile.closest("[data-wordbank-expandable-card]")).toHaveAttribute("data-state", "closed")
    fireEvent.click(tile)

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
  })

  it("opens the word page from the expanded paper surface", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          {
            lemma: "bog",
            english_translation: "book",
            variation_count: 1,
            pos_tags: ["NOUN"],
            categories: [],
          },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        is_sectioned: false,
        pos_tag: "NOUN",
        surface_forms: [],
      },
    })

    renderApp()
    const tile = await screen.findByRole("button", { name: "bog" })
    await act(async () => {
      tile.focus()
    })
    const surface = tile
      .closest<HTMLElement>("[data-wordbank-expandable-card]")
      ?.querySelector<HTMLElement>("[data-wordbank-expansion-surface]")
    fireEvent.click(surface!)

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
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

  it("keeps recency metadata off specimen tiles", async () => {
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
    expect(await screen.findByRole("button", { name: "bog" })).toHaveTextContent(/^bog$/)
    expect(screen.getByRole("button", { name: "bog" }).querySelector(".font-lexical")).toBeInTheDocument()
    expect(screen.queryByLabelText("Recently enriched bog")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Recently enriched gammel")).not.toBeInTheDocument()
  })

  it("renders all five references as a distinct deck shelf", async () => {
    mockFetchImplementation({ lemmasResponse: { items: [] } })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    const referenceShelf = await screen.findByRole("region", { name: "Reference collections" })
    expect(document.querySelector("[data-reference-drawer]")).toHaveClass("grid-cols-2", "@4xl:grid-cols-5")
    expect(within(referenceShelf).queryByRole("heading")).not.toBeInTheDocument()
    const labels = ["Pronouns", "HV Questions", "Prepositions", "Conjunctions", "Numbers & Time"]
    const tones = new Set<string>()
    for (const label of labels) {
      const deck = screen.getByRole("button", { name: `Open ${label} reference` })
      const material = deck.closest<HTMLElement>("[data-material='reference']")
      expect(material).toBeInTheDocument()
      expect(material).toHaveAttribute("data-paper-stock")
      expect(material).not.toHaveAttribute("data-paper-reveal")
      expect(deck.parentElement).toHaveClass("h-full")
      expect(deck.querySelector("svg[data-icon='inline-start']")).toHaveClass("mt-1.5", "self-start")
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
    expect(screen.getByRole("navigation", { name: "Word catalogue alphabet" }).firstElementChild)
      .toHaveClass("md:grid-cols-1")
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

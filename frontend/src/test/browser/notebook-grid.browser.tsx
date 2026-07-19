import "@/index.css"

import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { page } from "vitest/browser"
import { afterEach, expect, it } from "vitest"

import { PinnedWordCard } from "@/app/sections/wordbank/_shared/pinned-word-card"
import { WordbankListResults } from "@/app/sections/wordbank/wordbank-list-results"
import { mockFetchImplementation, renderApp } from "@/test/app-test-helpers"

const LEMMA = {
  lemma: "bog",
  display_lemma: "bog",
  english_translation: "book",
  created_at: "2026-07-16 08:00:00",
  last_enriched_at: "2026-07-17 08:00:00",
  variation_count: 1,
  pos_tags: ["NOUN"],
  categories: ["Reading"],
}

afterEach(() => cleanup())

async function settleLayout() {
  await new Promise<void>((resolve) => {
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => resolve()))
  })
}

function distanceToGrid(value: number, step: number): number {
  const remainder = ((value % step) + step) % step
  return Math.min(remainder, step - remainder)
}

async function expectNotebookAlignment() {
  await settleLayout()
  const inset = document.querySelector<HTMLElement>("[data-slot='sidebar-inset']")
  const sheet = document.querySelector<HTMLElement>("[data-notebook-sheet]")
  const content = document.querySelector<HTMLElement>("[data-notebook-content]")
  expect(inset).not.toBeNull()
  expect(sheet).not.toBeNull()
  expect(content).not.toBeNull()
  const insetStyle = window.getComputedStyle(inset!)
  expect(Number.parseFloat(insetStyle.borderTopLeftRadius)).toBeGreaterThan(0)
  expect(insetStyle.overflow).toBe("hidden")
  const contentRect = content!.getBoundingClientRect()
  const paddingTop = Number.parseFloat(window.getComputedStyle(content!).paddingTop)
  const origin = contentRect.top + paddingTop

  for (const anchor of document.querySelectorAll<HTMLElement>("[data-grid-anchor]")) {
    const step = anchor.dataset.gridAnchor === "rule" ? 32 : 8
    const distance = distanceToGrid(anchor.getBoundingClientRect().top - origin, step)
    const label = [
      anchor.tagName,
      anchor.dataset.gridAnchor,
      anchor.dataset.material,
      anchor.dataset.testid,
      anchor.className,
    ].filter(Boolean).join(" ")
    expect(
      distance,
      `${label} anchor (top ${anchor.getBoundingClientRect().top}, origin ${origin})`,
    ).toBeLessThanOrEqual(1)
  }

  for (const block of document.querySelectorAll<HTMLElement>("[data-grid-height='unit']")) {
    const distance = distanceToGrid(block.getBoundingClientRect().height, 8)
    expect(distance, `${block.tagName} height`).toBeLessThanOrEqual(1)
  }

  const wordbankList = document.querySelector("[data-grid-page='wordbank-list']")
  if (wordbankList) {
    const sheetStyle = window.getComputedStyle(sheet!)
    const wordMaterial = document.querySelector<HTMLElement>("[data-material='word']")
    expect(sheetStyle.backgroundImage).toBe("none")
    expect(sheetStyle.backgroundImage.match(/radial-gradient/g) ?? []).toHaveLength(0)
    expect(sheetStyle.backgroundImage.match(/repeating-linear-gradient/g) ?? []).toHaveLength(0)
    expect(window.getComputedStyle(wordMaterial!).backgroundImage)
      .toContain("/textures/wordbank-paper.webp")
    expect(wordMaterial).toHaveAttribute("data-paper-stock")
    const wordShadow = window.getComputedStyle(wordMaterial!).boxShadow
    expect(wordShadow).toContain("inset")
    expect(wordShadow).not.toMatch(/\b(?:2px|20px|40px|-28px)\b/)
    for (const material of wordbankList.querySelectorAll<HTMLElement>(
      "[data-material][data-paper-stock]",
    )) {
      const shadow = window.getComputedStyle(material).boxShadow
      expect(shadow).toContain("inset")
      expect(shadow).not.toMatch(/\b(?:2px|20px|40px|-28px)\b/)
    }
    const wordLabel = wordMaterial
      ?.closest("[data-wordbank-expandable-card]")
      ?.querySelector<HTMLElement>("[data-wordbank-expansion-title]")
    expect(wordLabel).not.toBeNull()
    expect(window.getComputedStyle(wordLabel!).fontFamily).toContain("Fraunces Variable")
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(window.innerWidth + 1)

    const wordTrigger = screen.getByRole("button", { name: "bog" })
    const expandableCard = wordTrigger.closest<HTMLElement>("[data-wordbank-expandable-card]")!
    const anchorBefore = expandableCard.getBoundingClientRect()
    await act(async () => {
      fireEvent.focus(wordTrigger)
      await new Promise((resolve) => window.setTimeout(resolve, 220))
    })
    await waitFor(() => {
      expect(expandableCard).toHaveAttribute("data-state", "open")
    })
    await settleLayout()
    const reveal = expandableCard.querySelector<HTMLElement>("[data-wordbank-expansion-surface]")!
    const triggerRect = wordTrigger.getBoundingClientRect()
    const revealRect = reveal.getBoundingClientRect()
    const anchorAfter = expandableCard.getBoundingClientRect()
    const titleRect = wordLabel!.getBoundingClientRect()
    expect(["up", "down"]).toContain(expandableCard.dataset.direction)
    if (expandableCard.dataset.direction === "up") {
      expect(Math.abs(revealRect.bottom - triggerRect.bottom)).toBeLessThanOrEqual(1)
    } else {
      expect(Math.abs(revealRect.top - triggerRect.top)).toBeLessThanOrEqual(1)
    }
    expect(Math.abs(anchorAfter.top - anchorBefore.top)).toBeLessThanOrEqual(1)
    expect(Math.abs(anchorAfter.height - anchorBefore.height)).toBeLessThanOrEqual(1)
    expect(window.getComputedStyle(wordLabel!).fontSize).toBe("20px")
    expect(Math.abs(titleRect.left - revealRect.left - 16)).toBeLessThanOrEqual(1)
    expect(Math.abs(titleRect.top - revealRect.top - 16)).toBeLessThanOrEqual(1)
    expect(window.getComputedStyle(wordTrigger).backgroundImage).toBe("none")
    expect(window.getComputedStyle(reveal).backgroundImage)
      .toContain("/textures/wordbank-paper.webp")
    expect(window.getComputedStyle(reveal).boxShadow).toContain("inset")
    expect(window.getComputedStyle(reveal).boxShadow)
      .not.toMatch(/\b(?:2px|20px|40px|-28px)\b/)
    expect(reveal.querySelector("[data-wordbank-specimen-preview]")).not.toHaveTextContent("bog")
    const revealBeforePreviewHover = reveal.getBoundingClientRect()
    await page.getByText("book", { exact: true }).hover()
    await settleLayout()
    const revealAfterPreviewHover = reveal.getBoundingClientRect()
    expect(window.getComputedStyle(reveal).transform).toBe("none")
    expect(revealAfterPreviewHover.top).toBeCloseTo(revealBeforePreviewHover.top, 1)
    expect(revealAfterPreviewHover.left).toBeCloseTo(revealBeforePreviewHover.left, 1)
    expect(revealRect.left).toBeGreaterThanOrEqual(15)
    expect(revealRect.right).toBeLessThanOrEqual(window.innerWidth - 15)
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(window.innerWidth + 1)
    await act(async () => {
      fireEvent.keyDown(wordTrigger, { key: "Escape" })
    })
    await waitFor(() => {
      expect(expandableCard).toHaveAttribute("data-state", "closed")
    })

    const alphabet = document.querySelector<HTMLElement>("[aria-label='Word catalogue alphabet']")
    const referenceDrawer = document.querySelector<HTMLElement>("[data-reference-drawer]")
    const referenceShelf = document.querySelector<HTMLElement>("[aria-label='Reference collections']")
    const filters = document.querySelector<HTMLElement>("[data-wordbank-filters]")
    const catalogue = document.querySelector<HTMLElement>("[data-wordbank-catalogue]")
    const bottomNav = document.querySelector<HTMLElement>("[data-slot='mobile-bottom-nav']")
    if (alphabet && bottomNav && window.getComputedStyle(bottomNav).display !== "none") {
      expect(alphabet.getBoundingClientRect().bottom).toBeLessThan(bottomNav.getBoundingClientRect().top)
    }

    const firstLetterGroup = document.querySelector<HTMLElement>("[data-wordbank-letter]")
    const letterHeading = firstLetterGroup?.querySelector<HTMLElement>("h3")
    const pageLeft = wordbankList.getBoundingClientRect().left
    for (const section of [referenceDrawer, filters, catalogue, letterHeading]) {
      if (section) {
        expect(Math.abs(section.getBoundingClientRect().left - pageLeft)).toBeLessThanOrEqual(1)
      }
    }
    if (referenceDrawer && filters && catalogue) {
      expect(filters.getBoundingClientRect().top - referenceDrawer.getBoundingClientRect().bottom).toBeGreaterThanOrEqual(31)
      expect(catalogue.getBoundingClientRect().top - filters.getBoundingClientRect().bottom).toBeGreaterThanOrEqual(31)
    }
    if (referenceShelf) {
      const shelfRight = referenceShelf.getBoundingClientRect().right
      for (const card of referenceShelf.querySelectorAll<HTMLElement>("[data-material='reference']")) {
        expect(card.getBoundingClientRect().right).toBeLessThanOrEqual(shelfRight + 1)
      }
    }
    if (letterHeading) {
      const letterStyle = window.getComputedStyle(letterHeading)
      expect(letterStyle.backgroundImage).toBe("none")
      expect(letterStyle.boxShadow).toBe("none")
    }
    if (alphabet && firstLetterGroup && window.innerWidth >= 768) {
      expect(alphabet.getBoundingClientRect().left).toBeGreaterThan(firstLetterGroup.getBoundingClientRect().left)
      expect(Math.abs(alphabet.getBoundingClientRect().right - wordbankList.getBoundingClientRect().right)).toBeLessThanOrEqual(1)
    }
  }
}

function mockNotebookPages() {
  mockFetchImplementation({
    lemmasResponse: { items: [LEMMA] },
    lemmaDetailsResponse: {
      lemma: "bog",
      english_translation: "book",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      categories: ["Reading"],
      is_sectioned: false,
      surface_forms: [
        {
          form: "bog",
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Ind",
          has_pronunciation: true,
        },
      ],
    },
  })
}

it.each([
  [390, 844],
  [768, 1024],
  [1280, 800],
  [1728, 900],
])("keeps the Wordbank sheet on the 8/32 grid at %ipx", async (width, height) => {
  await page.viewport(width, height)
  mockNotebookPages()
  renderApp()
  await screen.findByRole("heading", { name: "Words" })
  await expectNotebookAlignment()

  if (width === 1728) {
    const viewport = document.querySelector<HTMLElement>(".danote-notebook-viewport")
    const sheet = document.querySelector<HTMLElement>("[data-notebook-sheet]")
    const content = document.querySelector<HTMLElement>("[data-notebook-content]")
    expect(viewport).not.toBeNull()
    expect(sheet).not.toBeNull()
    expect(content).not.toBeNull()
    expect(Math.abs(sheet!.getBoundingClientRect().width - viewport!.clientWidth)).toBeLessThanOrEqual(1)
    expect(content!.getBoundingClientRect().width).toBeLessThanOrEqual(1280)
  }
})

it("keeps the paper hinge attached when collision places the preview below", async () => {
  await page.viewport(390, 320)
  render(
    <div className="w-64">
      <PinnedWordCard
        entry={{ lemma: "plantebog", translation: "field notebook" }}
        onOpenWord={() => undefined}
      />
    </div>,
  )

  const trigger = screen.getByRole("button", { name: /open plantebog in wordbank/i })
  await act(async () => {
    fireEvent.focus(trigger)
    await new Promise((resolve) => window.setTimeout(resolve, 120))
  })
  await waitFor(() => {
    expect(document.querySelector("[data-paper-reveal]")).toHaveAttribute("data-side", "bottom")
  })
  await settleLayout()

  const reveal = document.querySelector<HTMLElement>("[data-paper-reveal]")!
  expect(Math.abs(reveal.getBoundingClientRect().top - trigger.getBoundingClientRect().bottom))
    .toBeLessThanOrEqual(1)
  expect(Number.parseFloat(window.getComputedStyle(reveal, "::after").width))
    .toBeCloseTo(trigger.getBoundingClientRect().width, 0)
  expect(reveal.getBoundingClientRect().right).toBeLessThanOrEqual(window.innerWidth - 15)
})

it("expands a bottom-right specimen upward and left without moving its grid footprint", async () => {
  await page.viewport(390, 320)
  render(
    <div className="fixed right-4 bottom-4 flex w-64 flex-col gap-2">
      <div className="h-8" data-expansion-neighbor />
      <WordbankListResults
        lemmas={[LEMMA]}
        filters={{ posTags: [], categories: [] }}
        unreadWordbankLemmaCounts={new Map()}
        onSelectLemma={() => undefined}
        onRequestDelete={() => undefined}
        onClearFilters={() => undefined}
      />
    </div>,
  )

  const trigger = screen.getByRole("button", { name: "bog" })
  const card = trigger.closest<HTMLElement>("[data-wordbank-expandable-card]")!
  const neighbor = document.querySelector<HTMLElement>("[data-expansion-neighbor]")!
  const cardBefore = card.getBoundingClientRect()
  const neighborBefore = neighbor.getBoundingClientRect()

  await act(async () => {
    fireEvent.focus(trigger)
    await new Promise((resolve) => window.setTimeout(resolve, 220))
  })
  await waitFor(() => expect(card).toHaveAttribute("data-state", "open"))
  await settleLayout()

  const surface = card.querySelector<HTMLElement>("[data-wordbank-expansion-surface]")!
  const cardAfter = card.getBoundingClientRect()
  const surfaceRect = surface.getBoundingClientRect()
  expect(card).toHaveAttribute("data-direction", "up")
  expect(card).toHaveAttribute("data-align", "end")
  expect(Math.abs(surfaceRect.bottom - cardAfter.bottom)).toBeLessThanOrEqual(1)
  expect(Math.abs(surfaceRect.right - cardAfter.right)).toBeLessThanOrEqual(1)
  expect(surfaceRect.left).toBeGreaterThanOrEqual(15)
  expect(Math.abs(cardAfter.top - cardBefore.top)).toBeLessThanOrEqual(1)
  expect(Math.abs(cardAfter.height - cardBefore.height)).toBeLessThanOrEqual(1)
  expect(neighbor.getBoundingClientRect().top).toBeCloseTo(neighborBefore.top, 0)
  expect(Number.parseInt(window.getComputedStyle(card).zIndex, 10)).toBeGreaterThan(0)
})

it("keeps every reachable page inside the canonical notebook sheet", async () => {
  await page.viewport(1280, 800)
  mockNotebookPages()
  renderApp()
  await screen.findByRole("heading", { name: "Words" })

  fireEvent.click(await screen.findByRole("button", { name: "bog" }))
  await screen.findByRole("heading", { name: "bog" })
  expect(document.querySelector("[data-grid-page='wordbank-detail']")).toBeInTheDocument()
  await expectNotebookAlignment()

  fireEvent.click(screen.getByRole("button", { name: "Wordbank" }))
  await screen.findByRole("heading", { name: "Words" })
  fireEvent.click(screen.getByRole("button", { name: "Open Pronouns reference" }))
  await screen.findByRole("heading", { name: "Pronouns" })
  expect(document.querySelector("[data-grid-page='wordbank-reference']")).toBeInTheDocument()

  fireEvent.click(screen.getByRole("button", { name: "Sentencebank" }))
  await screen.findByRole("heading", { name: "Sentences" })
  await waitFor(() => {
    expect(document.querySelector("[data-grid-page='sentencebank-list']")).toBeInTheDocument()
  })

  fireEvent.click(screen.getByRole("button", { name: "Open account" }))
  await screen.findByRole("heading", { name: "Account" })
  expect(document.querySelector("[data-grid-page='account']")).toBeInTheDocument()

    fireEvent.click(screen.getByRole("button", { name: "Search" }))
  fireEvent.change(await screen.findByRole("textbox", { name: "command search" }), {
    target: { value: "chochito" },
  })
  fireEvent.click(await screen.findByText("Developer"))
  expect(await screen.findByText("Status")).toBeInTheDocument()
  expect(document.querySelector("[data-grid-page='developer']")).toBeInTheDocument()
  expect(document.querySelectorAll("[data-notebook-sheet]")).toHaveLength(1)
})

it.each([
  [390, 844],
  [1280, 800],
])("keeps the search folio tactile and contained at %ipx", async (width, height) => {
  await page.viewport(width, height)
  mockFetchImplementation({
    lemmasResponse: { items: [LEMMA] },
    searchWordbankResponse: {
      items: [{
        ...LEMMA,
        match_surface: "bog",
        query_cor_ids: [],
      }],
    },
  })
  renderApp()
  await screen.findByRole("heading", { name: "Words" })

    fireEvent.click(screen.getByRole("button", {
      name: width < 768 ? "Open search" : "Search",
    }))
  const dialog = await screen.findByRole("dialog", { name: "Find a word or sentence" })
  fireEvent.change(within(dialog).getByRole("textbox", { name: "command search" }), {
    target: { value: "bog" },
  })
  await within(dialog).findByText("In your notebook")

  const folio = dialog.querySelector<HTMLElement>("[data-search-folio]")!
  const composer = folio.querySelector<HTMLElement>("[data-search-composer]")!
  const list = folio.querySelector<HTMLElement>("[data-slot='command-list']")!
  const lexical = folio.querySelector<HTMLElement>("[data-search-lexical]")!
  const wordSlip = folio.querySelector<HTMLElement>("[data-search-slip][data-material='word']")!
  const toggle = folio.querySelector<HTMLElement>("[data-search-language-toggle]")!
  const controls = folio.querySelector<HTMLElement>("[data-search-folio-controls]")!
  const inputWrapper = folio.querySelector<HTMLElement>("[data-slot='command-input-wrapper']")!
  const searchIcon = folio.querySelector<HTMLElement>("[data-search-input-icon]")!
  const composerStyle = window.getComputedStyle(composer)
  const listStyle = window.getComputedStyle(list)
  const inputStyle = window.getComputedStyle(inputWrapper)
  const folioStyle = window.getComputedStyle(folio)
  expect(folio.scrollWidth).toBeLessThanOrEqual(folio.clientWidth + 1)
  expect(dialog.getBoundingClientRect().left).toBeGreaterThanOrEqual(-1)
  expect(dialog.getBoundingClientRect().right).toBeLessThanOrEqual(window.innerWidth + 1)
  expect(window.getComputedStyle(lexical).fontFamily).toContain("Fraunces Variable")
  expect(window.getComputedStyle(within(dialog).getByText("book")).fontFamily)
    .toContain("Source Sans 3")
  expect(wordSlip).toHaveAttribute("data-material", "word")
  expect(toggle.getBoundingClientRect().width).toBeGreaterThan(0)
  expect(controls).not.toHaveTextContent("Find a word or sentence")
  expect(controls.querySelector("#search-language-label")).toBeNull()
  expect(toggle.getBoundingClientRect().right).toBeGreaterThanOrEqual(controls.getBoundingClientRect().right - 24)
  expect(inputStyle.borderTopWidth).not.toBe("0px")
  expect(inputStyle.borderRadius).not.toBe("0px")
  expect(inputWrapper.getBoundingClientRect().height).toBeLessThanOrEqual(40)
  expect(Math.abs(
    searchIcon.getBoundingClientRect().top + searchIcon.getBoundingClientRect().height / 2
      - (inputWrapper.getBoundingClientRect().top + inputWrapper.getBoundingClientRect().height / 2),
  )).toBeLessThanOrEqual(1)
  expect(composerStyle.borderBottomWidth).toBe("0px")
  expect(listStyle.backgroundColor).toBe("rgba(0, 0, 0, 0)")
  expect(folioStyle.backgroundImage).toBe("none")
  expect(wordSlip).toHaveAttribute("data-material-tone")

  if (width < 768) {
    expect(list.getBoundingClientRect().bottom).toBeLessThanOrEqual(composer.getBoundingClientRect().top + 1)
    expect(composer.getBoundingClientRect().bottom).toBeLessThanOrEqual(window.innerHeight + 1)
  } else {
    expect(list.getBoundingClientRect().top).toBeGreaterThanOrEqual(composer.getBoundingClientRect().bottom - 1)
    expect(Math.abs(
      toggle.getBoundingClientRect().top + toggle.getBoundingClientRect().height / 2
        - (inputWrapper.getBoundingClientRect().top + inputWrapper.getBoundingClientRect().height / 2),
    )).toBeLessThanOrEqual(1)
    expect(inputWrapper.getBoundingClientRect().height).toBeCloseTo(toggle.getBoundingClientRect().height, 0)
    expect(dialog.getBoundingClientRect().width).toBeGreaterThanOrEqual(630)
  }
})

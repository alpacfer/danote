import "@/index.css"

import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react"
import { page } from "vitest/browser"
import { afterEach, expect, it } from "vitest"

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
    expect(sheetStyle.backgroundImage.match(/data:image\/svg\+xml/g) ?? []).toHaveLength(2)
    expect(sheetStyle.backgroundImage).toContain("radial-gradient")
    expect(sheetStyle.backgroundImage.match(/radial-gradient/g) ?? []).toHaveLength(1)
    expect(sheetStyle.backgroundImage.match(/repeating-linear-gradient/g) ?? []).toHaveLength(0)
    expect(sheetStyle.backgroundSize).toContain("8px 8px")
    expect(window.getComputedStyle(wordMaterial!).backgroundImage).toContain("data:image/svg+xml")
    expect(document.documentElement.scrollWidth).toBeLessThanOrEqual(window.innerWidth + 1)

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

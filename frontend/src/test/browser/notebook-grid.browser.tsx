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
  const sheet = document.querySelector<HTMLElement>("[data-notebook-sheet]")
  expect(sheet).not.toBeNull()
  const sheetRect = sheet!.getBoundingClientRect()
  const paddingTop = Number.parseFloat(window.getComputedStyle(sheet!).paddingTop)
  const origin = sheetRect.top + paddingTop

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
])("keeps the Wordbank sheet on the 8/32 grid at %ipx", async (width, height) => {
  await page.viewport(width, height)
  mockNotebookPages()
  renderApp()
  await screen.findByRole("heading", { name: "Words" })
  await expectNotebookAlignment()
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

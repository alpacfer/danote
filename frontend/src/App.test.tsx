import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react"
import { vi } from "vitest"
import { toast } from "sonner"

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

import App from "./App"

const SAVED_NOTES_STORAGE_KEY = "danote.saved-notes.v1"

afterEach(() => {
  vi.mocked(toast.success).mockReset()
  vi.mocked(toast.error).mockReset()
  vi.useRealTimers()
  vi.restoreAllMocks()
  window.localStorage.clear()
})

type AnalyzeToken = {
  surface_token: string
  normalized_token: string
  lemma_candidate: string | null
  pos_tag?: string | null
  morphology?: string | null
  classification: "known" | "variation" | "typo_likely" | "uncertain" | "new"
  match_source: "exact" | "lemma" | "none"
  matched_lemma: string | null
  matched_surface_form: string | null
  status?: "known" | "variation" | "typo_likely" | "uncertain" | "new"
  suggestions?: Array<{
    value: string
    score: number
    source_flags: string[]
  }>
  confidence?: number
  reason_tags?: string[]
  surface?: string
  normalized?: string
  lemma?: string | null
}

function responseOf(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response
}

function getNotesEditor(): HTMLElement {
  return screen.getByRole("textbox", { name: /lesson notes/i })
}

function setNotesEditorText(value: string) {
  const input = screen.getByTestId("lesson-notes-test-input")
  fireEvent.change(input, { target: { value } })
}

function mockFetchImplementation(options?: {
  healthOk?: boolean
  healthStatus?: "ok" | "degraded"
  analyzeOk?: boolean
  analyzeTokens?: AnalyzeToken[]
  analyzeHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  addWordOk?: boolean
  addWordResponse?: {
    status: "inserted" | "exists"
    stored_lemma: string
    stored_surface_form: string | null
    source: "manual"
    message: string
  }
  addWordHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  lemmasOk?: boolean
  lemmasResponse?: {
    items: Array<{
      lemma: string
      variation_count: number
      english_translation?: string | null
    }>
  }
  lemmaDetailsOk?: boolean
  lemmaDetailsResponse?: {
    lemma: string
    english_translation?: string | null
    surface_forms: Array<{
      form: string
      english_translation: string | null
    }>
  }
  resetDbOk?: boolean
  resetDbResponse?: {
    status: "reset"
    message: string
  }
  resetDbHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
  translationResponse?: {
    status: "generated" | "unavailable"
    source_word: string
    lemma: string
    english_translation: string | null
  }
  translationHandler?: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>
}) {
  const healthOk = options?.healthOk ?? true
  const healthStatus = options?.healthStatus ?? "ok"
  const analyzeOk = options?.analyzeOk ?? true
  const analyzeTokens = options?.analyzeTokens ?? []
  const addWordOk = options?.addWordOk ?? true
  const addWordResponse = options?.addWordResponse ?? {
    status: "inserted" as const,
    stored_lemma: "kat",
    stored_surface_form: "kat",
    source: "manual" as const,
    message: "Added 'kat' to wordbank.",
  }
  const lemmasOk = options?.lemmasOk ?? true
  const lemmasResponse = options?.lemmasResponse ?? { items: [] }
  const lemmaDetailsOk = options?.lemmaDetailsOk ?? true
  const lemmaDetailsResponse = options?.lemmaDetailsResponse ?? {
    lemma: "bog",
    english_translation: null,
    surface_forms: [{ form: "bogen", english_translation: null }],
  }
  const resetDbOk = options?.resetDbOk ?? true
  const resetDbResponse = options?.resetDbResponse ?? { status: "reset" as const, message: "Database reset complete." }
  const translationResponse = options?.translationResponse ?? {
    status: "unavailable" as const,
    source_word: "kat",
    lemma: "kat",
    english_translation: null,
  }

  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input)

    if (url.endsWith("/api/health")) {
      if (!healthOk) {
        throw new Error("network down")
      }
      return responseOf({ status: healthStatus, service: "backend" })
    }

    if (url.endsWith("/api/analyze")) {
      if (options?.analyzeHandler) {
        return options.analyzeHandler(input, init)
      }
      if (!analyzeOk) {
        throw new Error("analyze request failed")
      }
      return responseOf({ tokens: analyzeTokens })
    }

    if (url.endsWith("/api/wordbank/lexemes")) {
      if (options?.addWordHandler) {
        return options.addWordHandler(input, init)
      }
      if (!addWordOk) {
        throw new Error("add word request failed")
      }
      return responseOf(addWordResponse)
    }

    if (url.endsWith("/api/wordbank/lemmas")) {
      if (!lemmasOk) {
        throw new Error("wordbank request failed")
      }
      return responseOf(lemmasResponse)
    }

    if (url.includes("/api/wordbank/lemmas/")) {
      if (!lemmaDetailsOk) {
        throw new Error("word details request failed")
      }
      return responseOf(lemmaDetailsResponse)
    }

    if (url.endsWith("/api/wordbank/database")) {
      if (options?.resetDbHandler) {
        return options.resetDbHandler(input, init)
      }
      if (!resetDbOk) {
        throw new Error("reset database request failed")
      }
      return responseOf(resetDbResponse)
    }

    if (url.endsWith("/api/tokens/feedback")) {
      return responseOf({ status: "recorded" })
    }

    if (url.endsWith("/api/tokens/ignore")) {
      return responseOf({ status: "ignored" })
    }

    if (url.endsWith("/api/wordbank/translation")) {
      if (options?.translationHandler) {
        return options.translationHandler(input, init)
      }
      return responseOf(translationResponse)
    }

    return { ok: false, status: 404 } as Response
  })
}

describe("App shell", () => {
  it("renders header, lesson notes card, and backend status badge", async () => {
    mockFetchImplementation()

    render(<App />)

    expect(screen.getAllByText(/danote/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
    expect(getNotesEditor()).toBeInTheDocument()
    const statusBadge = await screen.findByLabelText("backend-connection-status")
    expect(statusBadge).toHaveTextContent(/connected/i)
  })

  it("renders sidebar navigation with playground, notes, and wordbank", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    expect(screen.getByRole("button", { name: /playground/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^notes$/i })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /wordbank/i })).toBeInTheDocument()
  })

  it("command dialog search opens centered and resolves variation plus notes", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 1, english_translation: "book" },
          { lemma: "hus", variation_count: 1, english_translation: "house" },
        ],
      },
      analyzeHandler: async (_input, init) => {
        const payload = JSON.parse(String(init?.body ?? "{}")) as { text?: string }
        if (payload.text === "bogen") {
          return responseOf({
            tokens: [
              {
                surface_token: "bogen",
                normalized_token: "bogen",
                lemma_candidate: "bog",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "bog",
                matched_surface_form: null,
              },
            ],
          })
        }
        return responseOf({ tokens: [] })
      },
    })
    window.localStorage.setItem(
      SAVED_NOTES_STORAGE_KEY,
      JSON.stringify([
        {
          id: "note-1",
          name: "Bogen note",
          text: "Jeg laeser en bog i dag",
          tokens: [],
          discoveredTokenMetadata: {},
          generatedTranslationMap: {},
          savedAt: "2026-02-28T12:00:00.000Z",
        },
      ]),
    )

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    expect(commandDialog).toBeInTheDocument()
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "bogen" } })

    expect(await screen.findByText(/^book$/i)).toBeInTheDocument()
    expect(await screen.findByText(/variation match: bogen/i)).toBeInTheDocument()
    const addVariationButton = await screen.findByText(/add variation "bogen"/i)
    fireEvent.click(addVariationButton)
    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes")) {
            return false
          }
          const body = JSON.parse(String(init?.body ?? "{}")) as {
            surface_token?: string
            lemma_candidate?: string
          }
          return body.surface_token === "bogen" && body.lemma_candidate === "bog"
        }),
      ).toBe(true)
    })

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialogAgain = await screen.findByRole("dialog")
    const searchInputAgain = within(commandDialogAgain).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInputAgain, { target: { value: "bog" } })
    const savedNoteResult = await screen.findByText(/bogen note/i)
    fireEvent.click(savedNoteResult)

    expect(await screen.findByRole("button", { name: /create new note/i })).toBeInTheDocument()
    expect(getNotesEditor()).toHaveTextContent(/jeg laeser en bog i dag/i)
  })

  it("command search offers adding a generated new word when there is no match", async () => {
    const fetchSpy = mockFetchImplementation({
      lemmasResponse: { items: [] },
      analyzeHandler: async (_input, init) => {
        const payload = JSON.parse(String(init?.body ?? "{}")) as { text?: string }
        if (payload.text === "snakker") {
          return responseOf({
            tokens: [
              {
                surface_token: "snakker",
                normalized_token: "snakker",
                lemma_candidate: "snakke",
                classification: "new",
                match_source: "none",
                matched_lemma: null,
                matched_surface_form: null,
              },
            ],
          })
        }
        return responseOf({ tokens: [] })
      },
      translationHandler: async () =>
        responseOf({
          status: "generated",
          source_word: "snakker",
          lemma: "snakke",
          english_translation: "talks",
        }),
      addWordResponse: {
        status: "inserted",
        stored_lemma: "snakke",
        stored_surface_form: "snakker",
        source: "manual",
        message: "Added 'snakke' to wordbank.",
      },
    })

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    const searchInput = within(commandDialog).getByPlaceholderText(/search words and notes/i)
    fireEvent.change(searchInput, { target: { value: "snakker" } })

    expect(await screen.findByText(/add "snakker" to wordbank/i)).toBeInTheDocument()
    expect(await screen.findByText(/lemma: snakke/i)).toBeInTheDocument()
    expect(await screen.findByText(/^talks$/i)).toBeInTheDocument()

    fireEvent.click(screen.getByText(/add "snakker" to wordbank/i))

    await waitFor(() => {
      expect(
        fetchSpy.mock.calls.some(([input, init]) => {
          if (!String(input).endsWith("/api/wordbank/lexemes")) {
            return false
          }
          const body = JSON.parse(String(init?.body ?? "{}")) as {
            surface_token?: string
            lemma_candidate?: string
          }
          return body.surface_token === "snakker" && body.lemma_candidate === "snakke"
        }),
      ).toBe(true)
    })
  })

  it("saves a named note with analysis and reopens it in playground", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    fireEvent.click(screen.getByRole("button", { name: /save note/i }))
    const saveDialog = await screen.findByRole("dialog")
    const noteNameInput = within(saveDialog).getByLabelText(/note name/i)
    expect(noteNameInput).toHaveAttribute("autocomplete", "off")
    fireEvent.change(noteNameInput, {
      target: { value: "My saved note" },
    })
    fireEvent.click(within(saveDialog).getByRole("button", { name: /^save$/i }))
    await waitFor(() => {
      expect(screen.getByLabelText("note-autosave-status")).toHaveTextContent(/autosaved/i)
    })

    expect(screen.getByRole("button", { name: /create new note/i })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: /create new note/i }))
    const createDialog = await screen.findByRole("dialog")
    expect(within(createDialog).getByText(/current note will be saved/i)).toBeInTheDocument()
    expect(within(createDialog).getByLabelText(/new note name/i)).toBeInTheDocument()
    fireEvent.click(within(createDialog).getByRole("button", { name: /cancel/i }))

    fireEvent.click(screen.getByRole("button", { name: /^notes$/i }))
    const savedCardButton = await screen.findByRole("button", { name: /my saved note/i })
    expect(savedCardButton).toBeInTheDocument()
    expect(savedCardButton).toHaveTextContent("katten")
    expect(screen.queryByRole("button", { name: /open in playground/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/known/i)).not.toBeInTheDocument()

    fireEvent.click(savedCardButton)
    expect(await screen.findByRole("button", { name: /create new note/i })).toBeInTheDocument()
    expect(getNotesEditor()).toHaveTextContent("katten")
  })

  it("shows saved lemmas in wordbank and opens lemma details page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 2 },
          { lemma: "hus", variation_count: 1 },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        surface_forms: [
          { form: "bogen", english_translation: "book" },
          { form: "bogens", english_translation: "book's" },
        ],
      },
    })

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    const bogItem = await screen.findByRole("button", { name: /bog/i })
    expect(bogItem).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /hus/i })).toBeInTheDocument()

    fireEvent.click(bogItem)
    expect(await screen.findByText(/^bog$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^book$/i)).toBeInTheDocument()
    expect(screen.getByText(/^book's$/i)).toBeInTheDocument()
  })

  it("shows lesson notes in playground", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByText(/connected/i)

    expect(screen.getAllByText(/lesson notes/i).length).toBeGreaterThan(0)
  })

  it("renders offline status when health check fails", async () => {
    mockFetchImplementation({ healthOk: false })

    render(<App />)

    expect(await screen.findByText(/offline/i)).toBeInTheDocument()
  })

  it("renders degraded status when backend health is degraded", async () => {
    mockFetchImplementation({ healthStatus: "degraded" })

    render(<App />)

    expect(await screen.findByText(/degraded/i)).toBeInTheDocument()
  })

  it("notes editor accepts typing and paste-like updates", async () => {
    mockFetchImplementation()

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    const editor = getNotesEditor()
    expect(editor).toHaveAttribute("spellcheck", "false")
    expect(editor).toHaveAttribute("autocorrect", "off")
    expect(editor).toHaveAttribute("autocapitalize", "off")
    expect(editor).toHaveAttribute("autocomplete", "off")

    setNotesEditorText("Jeg kan godt lide bogen")
    expect(getNotesEditor()).toHaveTextContent("Jeg kan godt lide bogen")

    setNotesEditorText("linje 1\nlinje 2")
    expect(getNotesEditor()).toHaveTextContent(/linje 1/i)
    expect(getNotesEditor()).toHaveTextContent(/linje 2/i)
  })

  it("debounce collapses rapid typing into one analyze call", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({ tokens: [] })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("Jeg")
    setNotesEditorText("Jeg kan")
    setNotesEditorText("Jeg kan godt lide bogen ")

    await act(async () => {
      await vi.advanceTimersByTimeAsync(400)
    })
    expect(analyzeBodies).toHaveLength(0)

    await act(async () => {
      await vi.advanceTimersByTimeAsync(100)
      await Promise.resolve()
    })
    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "Jeg kan godt lide bogen" }))
  })

  it("does not analyze unfinished trailing token until finalization", async () => {
    vi.useFakeTimers()
    const analyzeBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        analyzeBodies.push(String(init?.body ?? ""))
        return responseOf({
          tokens: [
            {
              surface_token: "bogen",
              normalized_token: "bogen",
              lemma_candidate: "bog",
              classification: "variation",
              match_source: "lemma",
              matched_lemma: "bog",
              matched_surface_form: null,
            },
          ],
        })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")
    setNotesEditorText("b")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("bo")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("boge")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    setNotesEditorText("bogen")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(analyzeBodies).toHaveLength(0)

    setNotesEditorText("bogen ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    expect(analyzeBodies).toHaveLength(1)
    expect(analyzeBodies[0]).toBe(JSON.stringify({ text: "bogen" }))

    expect(screen.getAllByText(/^bogen$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("stale responses do not overwrite newer results", async () => {
    vi.useFakeTimers()
    const resolvers: Array<(value: Response) => void> = []

    mockFetchImplementation({
      analyzeHandler: () =>
        new Promise<Response>((resolve) => {
          resolvers.push(resolve)
        }),
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("første ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    setNotesEditorText("anden ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })

    expect(resolvers).toHaveLength(2)

    await act(async () => {
      resolvers[1](
        responseOf({
          tokens: [
            {
              surface_token: "anden",
              normalized_token: "anden",
              lemma_candidate: "anden",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)

    await act(async () => {
      resolvers[0](
        responseOf({
          tokens: [
            {
              surface_token: "første",
              normalized_token: "første",
              lemma_candidate: "første",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      )
      await Promise.resolve()
    })

    expect(screen.queryByText(/^første$/i)).not.toBeInTheDocument()
    expect(screen.getAllByText(/^anden$/i).length).toBeGreaterThanOrEqual(1)
  })

  it("highlights new, variation, and typo_likely tokens in the editor", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "bogen",
          normalized_token: "bogen",
          lemma_candidate: "bog",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "bog",
          matched_surface_form: null,
        },
        {
          surface_token: "spisr",
          normalized_token: "spisr",
          lemma_candidate: "spiser",
          classification: "typo_likely",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "nyord",
          normalized_token: "nyord",
          lemma_candidate: "nyord",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kan bogen spisr nyord ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const editor = getNotesEditor()
    expect(editor.querySelector('mark[data-status="variation"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="typo_likely"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="new"]')).toBeInTheDocument()
  })

  it("does not visually highlight uncertain tokens and keeps known tokens unstyled", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kan",
          normalized_token: "kan",
          lemma_candidate: "kan",
          classification: "known",
          match_source: "exact",
          matched_lemma: "kan",
          matched_surface_form: "kan",
        },
        {
          surface_token: "MilkoScna",
          normalized_token: "milkoscna",
          lemma_candidate: null,
          classification: "uncertain",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kan MilkoScna ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const editor = getNotesEditor()
    expect(editor.querySelector('mark[data-status="known"]')).toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="uncertain"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="new"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="variation"]')).not.toBeInTheDocument()
    expect(editor.querySelector('mark[data-status="typo_likely"]')).not.toBeInTheDocument()
  })

  it("highlights full words at the start of each new line", async () => {
    vi.useFakeTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "asdfsadf",
          normalized_token: "asdfsadf",
          lemma_candidate: "asdfsadf",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
        {
          surface_token: "komputer",
          normalized_token: "komputer",
          lemma_candidate: "komputer",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "dyr",
          normalized_token: "dyr",
          lemma_candidate: "dyr",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("asdfsadf\n\nkatten \n\nkomputer\n\ndyr ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
      await Promise.resolve()
    })

    const marks = Array.from(getNotesEditor().querySelectorAll("mark")).map((node) => node.textContent)
    expect(marks).toEqual(expect.arrayContaining(["asdfsadf", "katten", "komputer", "dyr"]))
    expect(marks).not.toContain("atten")
    expect(marks).not.toContain("mputer")
  })

  it("clicking a highlighted noun opens noun popover with word, lemma subtitle, and translation", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      lemmasResponse: {
        items: [],
      },
      translationResponse: {
        status: "generated",
        source_word: "katten",
        lemma: "kat",
        english_translation: "cat",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    const addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^katten$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^kat \(en\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^katten \(en\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^NOUN$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^cat$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^Morphology: /i)).not.toBeInTheDocument()
  })

  it("clicking a known word opens popover with wordbank action instead of add", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "bogen",
          normalized_token: "bogen",
          lemma_candidate: "bog",
          classification: "known",
          match_source: "exact",
          matched_lemma: "bog",
          matched_surface_form: "bogen",
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2, english_translation: "book" }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        surface_forms: [{ form: "bogen", english_translation: "book" }],
      },
      translationResponse: {
        status: "generated",
        source_word: "bogen",
        lemma: "bog",
        english_translation: "book",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("bogen ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='known']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='known']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    const openButton = await screen.findByRole("button", { name: /open in wordbank/i })
    const popoverContent = openButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^bogen$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^bog \(en\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^bogen \(en\)$/i)).not.toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^NOUN$/i)).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /add to wordbank/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /add variation/i })).not.toBeInTheDocument()

    fireEvent.click(openButton)
    expect(await screen.findByText(/^bog$/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/^book$/i)).length).toBeGreaterThanOrEqual(1)
  })

  it("noun popover hides duplicate lemma and shows translation skeleton when unavailable", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "hus",
          normalized_token: "hus",
          lemma_candidate: "hus",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Neut|Number=Sing|Definite=Ind",
        },
      ],
      translationResponse: {
        status: "unavailable",
        source_word: "hus",
        lemma: "hus",
        english_translation: null,
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("hus ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 180, clientY: 160 })

    const addButton = await screen.findByRole("button", { name: /add to wordbank/i })
    const popoverContent = addButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^hus$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^hus \(et\)$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByTestId("noun-translation-skeleton")).toBeInTheDocument()
  })

  it("verb popover shows infinitive subtitle and present form in the title", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spiser",
          normalized_token: "spiser",
          lemma_candidate: "spise",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "spise",
          matched_surface_form: null,
          pos_tag: "VERB",
          morphology: "Mood=Ind|Tense=Pres|VerbForm=Fin",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "spiser",
        lemma: "spise",
        english_translation: "eat",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("spiser ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 180, clientY: 150 })

    const addButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^spiser$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^at spise$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^VERB$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Present$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^eat$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^Morphology: /i)).not.toBeInTheDocument()
  })

  it("verb popover maps participle morphology to past participle label in title", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spist",
          normalized_token: "spist",
          lemma_candidate: "spise",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "spise",
          matched_surface_form: null,
          pos_tag: "VERB",
          morphology: "Tense=Past|VerbForm=Part",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "spist",
        lemma: "spise",
        english_translation: "eaten",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("spist ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 190, clientY: 155 })

    expect(await screen.findByText(/^Past participle$/i)).toBeInTheDocument()
  })

  it("remembers discovered verb metadata and reuses translation when later analysis degrades to X", async () => {
    vi.useRealTimers()
    let translationCalls = 0

    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        const rawBody = String(init?.body ?? "{}")
        const payload = JSON.parse(rawBody) as { text?: string }

        if (payload.text === "hedde") {
          return responseOf({
            tokens: [
              {
                surface_token: "hedde",
                normalized_token: "hedde",
                lemma_candidate: "hedde",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "hedde",
                matched_surface_form: null,
                pos_tag: "VERB",
                morphology: "VerbForm=Inf",
              },
            ],
          })
        }

        if (payload.text === "hedde vinteren") {
          return responseOf({
            tokens: [
              {
                surface_token: "hedde",
                normalized_token: "hedde",
                lemma_candidate: "hedde",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "hedde",
                matched_surface_form: null,
                pos_tag: "X",
                morphology: null,
              },
              {
                surface_token: "vinteren",
                normalized_token: "vinteren",
                lemma_candidate: "vinter",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "vinter",
                matched_surface_form: null,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Definite=Def|Number=Sing",
              },
            ],
          })
        }

        return responseOf({ tokens: [] })
      },
      translationHandler: async () => {
        translationCalls += 1
        return responseOf({
          status: "generated",
          source_word: "hedde",
          lemma: "hedde",
          english_translation: "be called",
        })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("hedde ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    let heddeMark = Array.from(getNotesEditor().querySelectorAll("mark[data-status='variation']")).find(
      (node) => node.textContent?.toLowerCase() === "hedde",
    )
    expect(heddeMark).toBeInTheDocument()
    fireEvent.click(heddeMark as HTMLElement, { clientX: 170, clientY: 145 })

    expect(await screen.findByText(/^VERB$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^at hedde$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^be called$/i)).toBeInTheDocument()
    expect(translationCalls).toBe(1)

    setNotesEditorText("hedde vinteren ")
    await waitFor(() => {
      const marks = getNotesEditor().querySelectorAll("mark[data-status='variation']")
      expect(marks.length).toBeGreaterThanOrEqual(2)
    })

    heddeMark = Array.from(getNotesEditor().querySelectorAll("mark[data-status='variation']")).find(
      (node) => node.textContent?.toLowerCase() === "hedde",
    )
    expect(heddeMark).toBeInTheDocument()
    fireEvent.click(heddeMark as HTMLElement, { clientX: 172, clientY: 147 })

    expect(await screen.findByText(/^VERB$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^at hedde$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^be called$/i)).toBeInTheDocument()
    expect(translationCalls).toBe(1)
  })

  it("updates popover fields when context changes a word to a new POS", async () => {
    mockFetchImplementation({
      analyzeHandler: async (_input, init) => {
        const body = JSON.parse(String(init?.body ?? "{}")) as { text?: string }
        const text = body.text ?? ""
        if (text.trim() === "det") {
          return responseOf({
            tokens: [
              {
                surface_token: "det",
                normalized_token: "det",
                lemma_candidate: "den",
                pos_tag: "PRON",
                morphology: "Person=3|Number=Sing|PronType=Prs",
                classification: "variation",
                match_source: "lemma",
                matched_lemma: "den",
                matched_surface_form: "det",
              },
            ],
          })
        }
        return responseOf({
          tokens: [
            {
              surface_token: "det",
              normalized_token: "det",
              lemma_candidate: "den",
              pos_tag: "DET",
              morphology: "Gender=Neut|Number=Sing|PronType=Art",
              classification: "variation",
              match_source: "lemma",
              matched_lemma: "den",
              matched_surface_form: "det",
            },
            {
              surface_token: "hus",
              normalized_token: "hus",
              lemma_candidate: "hus",
              pos_tag: "NOUN",
              morphology: "Gender=Neut|Number=Sing",
              classification: "new",
              match_source: "none",
              matched_lemma: null,
              matched_surface_form: null,
            },
          ],
        })
      },
      translationResponse: {
        status: "generated",
        source_word: "det",
        lemma: "den",
        english_translation: "it",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("det ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    let detMark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(detMark as HTMLElement, { clientX: 150, clientY: 130 })

    let addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    let popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^PRON$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^3rd person$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Singular$/i)).toBeInTheDocument()

    setNotesEditorText("det hus ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    detMark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(detMark as HTMLElement, { clientX: 152, clientY: 132 })

    addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    await waitFor(() => {
      expect(within(popoverContent as HTMLElement).getByText(/^DET$/)).toBeInTheDocument()
    })
    expect(within(popoverContent as HTMLElement).getByText(/^t-word$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Singular$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).queryByText(/^3rd person$/i)).not.toBeInTheDocument()
  })

  it("clicking a typo_likely highlight does not open popover or request translation", async () => {
    vi.useRealTimers()
    const fetchSpy = mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "spisr",
          normalized_token: "spisr",
          lemma_candidate: "spiser",
          classification: "typo_likely",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationHandler: async () => {
        throw new Error("translation endpoint should not be called for typo_likely")
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("spisr ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='typo_likely']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='typo_likely']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.queryByText(/^translations$/i)).not.toBeInTheDocument()
    const translationCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/wordbank/translation"),
    )
    expect(translationCalls).toHaveLength(0)
  })

  it("does not highlight proper nouns or numerals or open popover for them", async () => {
    const fetchSpy = mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "København",
          normalized_token: "københavn",
          lemma_candidate: "København",
          pos_tag: "PROPN",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
        {
          surface_token: "42",
          normalized_token: "42",
          lemma_candidate: "42",
          pos_tag: "NUM",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationHandler: async () => {
        throw new Error("translation endpoint should not be called for proper nouns or numerals")
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("København 42 ")
    await waitFor(() => {
      expect(getNotesEditor().querySelector("mark")).not.toBeInTheDocument()
    })

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.queryByText(/^translations$/i)).not.toBeInTheDocument()
    const translationCalls = fetchSpy.mock.calls.filter(([input]) =>
      String(input).endsWith("/api/wordbank/translation"),
    )
    expect(translationCalls).toHaveLength(0)
  })

  it("adjective popover shows gender and number with translation", async () => {
    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "stor",
          normalized_token: "stor",
          lemma_candidate: "stor",
          pos_tag: "ADJ",
          morphology: "Degree=Pos|Gender=Com|Number=Plur",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "stor",
        lemma: "stor",
        english_translation: "big",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")
    setNotesEditorText("stor ")

    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 140, clientY: 120 })

    expect(await screen.findByText(/^ADJ$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^Common$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^Plural$/i)).toBeInTheDocument()
    expect(await screen.findByText(/^big$/i)).toBeInTheDocument()
  })

  it("aux popover follows verb layout and shows translation", async () => {
    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "har",
          normalized_token: "har",
          lemma_candidate: "have",
          pos_tag: "AUX",
          morphology: "Mood=Ind|Tense=Pres|VerbForm=Fin",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "have",
          matched_surface_form: "have",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "har",
        lemma: "have",
        english_translation: "have",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")
    setNotesEditorText("har ")

    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    fireEvent.click(mark as HTMLElement, { clientX: 150, clientY: 130 })

    const addVariationButton = await screen.findByRole("button", { name: /add variation/i })
    const popoverContent = addVariationButton.closest('[data-slot="popover-content"]')
    expect(popoverContent).not.toBeNull()
    expect(within(popoverContent as HTMLElement).getByText(/^AUX$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^Present$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^at have$/i)).toBeInTheDocument()
    expect(within(popoverContent as HTMLElement).getByText(/^have$/i)).toBeInTheDocument()
  })

  it("keeps editor focus when opening popover and dismisses popover when typing", async () => {
    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "katten",
          normalized_token: "katten",
          lemma_candidate: "kat",
          classification: "variation",
          match_source: "lemma",
          matched_lemma: "kat",
          matched_surface_form: null,
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Sing|Definite=Def",
        },
      ],
      translationResponse: {
        status: "generated",
        source_word: "katten",
        lemma: "kat",
        english_translation: "cat",
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("katten ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='variation']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='variation']")
    expect(mark).toBeInTheDocument()
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    expect(await screen.findByRole("button", { name: /add variation/i })).toBeInTheDocument()
    expect(getNotesEditor().contains(document.activeElement)).toBe(true)

    setNotesEditorText("katten x")
    await waitFor(() => {
      expect(screen.queryByRole("button", { name: /add variation/i })).not.toBeInTheDocument()
    })
  })

  it("adding from popover calls backend, re-analyzes, and shows success toast", async () => {
    vi.useRealTimers()
    let analyzeCallCount = 0
    const addBodies: string[] = []

    mockFetchImplementation({
      analyzeHandler: async () => {
        analyzeCallCount += 1
        if (analyzeCallCount === 1) {
          return responseOf({
            tokens: [
              {
                surface_token: "kat",
                normalized_token: "kat",
                lemma_candidate: "kat",
                classification: "new",
                match_source: "none",
                matched_lemma: null,
                matched_surface_form: null,
              },
            ],
          })
        }
        return responseOf({
          tokens: [
            {
              surface_token: "kat",
              normalized_token: "kat",
              lemma_candidate: "kat",
              classification: "known",
              match_source: "exact",
              matched_lemma: "kat",
              matched_surface_form: "kat",
            },
          ],
        })
      },
      addWordHandler: async (_input, init) => {
        addBodies.push(String(init?.body ?? ""))
        return responseOf({
          status: "inserted",
          stored_lemma: "kat",
          stored_surface_form: "kat",
          source: "manual",
          message: "Added 'kat' to wordbank.",
        })
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kat ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    fireEvent.click(await screen.findByRole("button", { name: /add to wordbank/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })
    await waitFor(async () => {
      await Promise.resolve()
      await Promise.resolve()
      expect(analyzeCallCount).toBeGreaterThanOrEqual(2)
    })

    expect(addBodies).toHaveLength(1)
    expect(addBodies[0]).toBe(JSON.stringify({ surface_token: "kat", lemma_candidate: "kat" }))
    expect(vi.mocked(toast.success)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Added 'kat' to wordbank.")
  })

  it("shows error toast when popover add fails", async () => {
    vi.useRealTimers()

    mockFetchImplementation({
      analyzeTokens: [
        {
          surface_token: "kat",
          normalized_token: "kat",
          lemma_candidate: "kat",
          classification: "new",
          match_source: "none",
          matched_lemma: null,
          matched_surface_form: null,
        },
      ],
      addWordOk: false,
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("kat ")
    await waitFor(() => {
      const mark = getNotesEditor().querySelector("mark[data-status='new']")
      expect(mark).toBeInTheDocument()
    })

    const mark = getNotesEditor().querySelector("mark[data-status='new']")
    fireEvent.click(mark as HTMLElement, { clientX: 160, clientY: 140 })

    fireEvent.click(await screen.findByRole("button", { name: /add to wordbank/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(vi.mocked(toast.error)).toHaveBeenCalledTimes(1)
    expect(vi.mocked(toast.error)).toHaveBeenCalledWith("add word request failed")
  })


  it("shows NLP model picker in developer options", async () => {
    mockFetchImplementation({})

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))

    const modelPicker = screen.getByRole("combobox", { name: /nlp model picker/i })
    expect(modelPicker).toBeInTheDocument()
    expect(modelPicker).toHaveTextContent("da_dacy_small_trf-0.2.0")

    expect(screen.getByText(/backend default remains/i)).toBeInTheDocument()
  })

  it("deletes complete db from developer options", async () => {
    const resetMethods: Array<string | undefined> = []
    vi.spyOn(window, "confirm").mockReturnValue(true)
    mockFetchImplementation({
      resetDbHandler: async (_input, init) => {
        resetMethods.push(init?.method)
        return responseOf({ status: "reset", message: "Database reset complete." })
      },
    })

    render(<App />)
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /developer/i }))
    fireEvent.click(screen.getByRole("button", { name: /delete complete db/i }))

    await act(async () => {
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(resetMethods).toEqual(["DELETE"])
    expect(vi.mocked(toast.success)).toHaveBeenCalledWith("Database reset complete.")
  })

  it("renders analysis error state", async () => {
    vi.useFakeTimers()
    let fail = false

    mockFetchImplementation({
      analyzeHandler: async () => {
        if (fail) {
          throw new Error("backend unavailable")
        }
        return new Promise<Response>(() => {})
      },
    })

    render(<App />)
    screen.getByLabelText("backend-connection-status")

    setNotesEditorText("test ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(500)
    })
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()

    fail = true
    setNotesEditorText("test2 ")
    await act(async () => {
      await vi.advanceTimersByTimeAsync(600)
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(screen.getByRole("alert")).toHaveTextContent(/backend unavailable/i)
  })
})

import { fireEvent, getNotesEditor, mockFetchImplementation, renderApp, screen, setNotesEditorText, vi, waitFor, within } from "@/test/app-test-helpers"

describe("App notes", () => {
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

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    expect(screen.getByRole("button", { name: /no unread notifications/i })).toBeDisabled()

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
    const notificationButton = screen.getByRole("button", { name: /show notifications \(1 unread\)/i })
    expect(notificationButton).toBeEnabled()
    fireEvent.click(notificationButton)
    const notificationList = await screen.findByLabelText("notification-list")
    expect(notificationList).toHaveTextContent("Saved note: My saved note")

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
  }, 10_000)

})

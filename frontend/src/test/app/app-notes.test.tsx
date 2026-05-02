import { mockFetchImplementation, renderApp, screen, seedSavedNotes } from "@/test/app-test-helpers"

describe("App notes", () => {
  it("does not expose the retired Notes section", async () => {
    seedSavedNotes([
      {
        id: "note-1",
        name: "My saved note",
        text: "katten",
        savedAt: "2026-04-01T12:00:00.000Z",
        tokens: [],
        discoveredTokenMetadata: {},
        generatedTranslationMap: {},
      },
    ])
    mockFetchImplementation()

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    expect(screen.queryByRole("button", { name: /^notes$/i })).not.toBeInTheDocument()
    expect(screen.queryByText("My saved note")).not.toBeInTheDocument()
    expect(screen.queryByText("katten")).not.toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: /lesson notes/i })).not.toBeInTheDocument()
  })
})

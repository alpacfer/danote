import { fireEvent, mockFetchImplementation, renderApp, screen, seedSavedNotes } from "@/test/app-test-helpers"

describe("App notes", () => {
  it("shows saved notes without opening them into Playground", async () => {
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

    fireEvent.click(screen.getByRole("button", { name: /^notes$/i }))

    expect(await screen.findByText("My saved note")).toBeInTheDocument()
    expect(screen.getByText("katten")).toBeInTheDocument()
    expect(screen.queryByRole("button", { name: /my saved note/i })).not.toBeInTheDocument()
    expect(screen.queryByRole("textbox", { name: /lesson notes/i })).not.toBeInTheDocument()
  })
})

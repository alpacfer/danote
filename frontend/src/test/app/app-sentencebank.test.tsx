import { fireEvent, mockFetchImplementation, renderApp, screen } from "@/test/app-test-helpers"

describe("App sentencebank", () => {
  it("shows saved sentences in sentencebank", async () => {
    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 1,
            source_text: "Jeg elsker dansk",
            english_translation: "i love danish",
            created_at: "2026-02-28T12:00:00.000Z",
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /sentencebank/i }))

    expect(await screen.findByText(/jeg elsker dansk/i)).toBeInTheDocument()
    expect(screen.getByText(/i love danish/i)).toBeInTheDocument()
  })

})

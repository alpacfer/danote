import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, within } from "@/test/app-test-helpers"
import userEvent from "@testing-library/user-event"

// Locks in the visual contract for the shared word page: every word page (whether
// the lemma is user-saved or a built-in/presaved one) must render the same chrome
// at the top (lemma title + pronunciation + verification trigger) and the same
// structural layout inside the synthetic root card (lemma word + translation +
// POS badges + pinned-home chips). Saved and built-in pages must be 1:1 — the only
// difference is the verification overview state (built-ins read "Verified" by
// construction).
describe("App wordbank word-page parity", () => {
  function savedBogResponse() {
    return {
      lemma: "bog",
      english_translation: "book",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      is_sectioned: false,
      categories: ["Household Objects"],
      surface_forms: [
        { form: "bog", has_pronunciation: true, pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Ind" },
      ],
    }
  }

  function builtInHvorResponse() {
    return {
      lemma: "hvor",
      english_translation: "where",
      pos_tag: "ADV",
      morphology: "PronType=Int",
      is_sectioned: false,
      reference_links: [
        {
          page_id: "pronouns",
          page_title: "Pronouns",
          tab_id: "question_words",
          tab_title: "Question Words",
          sentinel: "__pinned_pronouns_question_words",
        },
      ],
      meaning_sections: [],
      surface_forms: [
        { form: "hvor", has_pronunciation: true, pos_tag: "ADV", morphology: "PronType=Int" },
      ],
    }
  }

  async function openSavedBogPage() {
    mockFetchImplementation({
      lemmasResponse: { items: [{ lemma: "bog", variation_count: 1 }] },
      lemmaDetailsResponse: savedBogResponse(),
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))
    await screen.findByRole("heading", { name: /^bog$/i })
  }

  async function openBuiltInHvorPage() {
    const user = userEvent.setup()
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (!url.endsWith("/api/wordbank/lemmas/hvor")) {
          throw new Error(`Unexpected lemma details request: ${url}`)
        }
        return responseOf(builtInHvorResponse())
      },
    })
    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(await screen.findByRole("button", { name: /open pronouns reference/i }))
    await user.click(screen.getByRole("tab", { name: /question words/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open hvor in wordbank/i }))
    await screen.findByRole("heading", { name: /^hvor$/i })
    return user
  }

  function describeWordPageLayout(lemma: string) {
    const heading = screen.getByRole("heading", { level: 2, name: new RegExp(`^${lemma}$`, "i") })
    const headingInsideCard = Boolean(heading.closest('[data-testid="wordbank-lemma-scope-card"]'))
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    const cardLemma = within(scopeCard).getByTestId("wordbank-lemma-card-lemma").textContent?.trim() ?? null
    const cardBadges = within(scopeCard).queryByTestId("wordbank-lemma-header-badges")
    const cardPinnedHome = within(scopeCard).queryByTestId("wordbank-pinned-home-card")
    const verificationButton = screen.getByRole("button", { name: /verification/i })
    const audioButton = screen.queryByRole("button", { name: new RegExp(`listen to ${lemma}`, "i") })

    return {
      hasTopHeading: Boolean(heading) && !headingInsideCard,
      hasScopeCard: Boolean(scopeCard),
      cardLemma,
      hasCardBadges: Boolean(cardBadges),
      hasPinnedHomeChip: Boolean(cardPinnedHome),
      hasVerificationTrigger: Boolean(verificationButton),
      hasAudioButton: Boolean(audioButton),
    }
  }

  it("renders the same structural primitives for a saved word", async () => {
    await openSavedBogPage()
    const saved = describeWordPageLayout("bog")
    expect(saved).toEqual({
      hasTopHeading: true,
      hasScopeCard: true,
      cardLemma: "bog",
      hasCardBadges: true,
      hasPinnedHomeChip: false,
      hasVerificationTrigger: true,
      hasAudioButton: true,
    })
  })

  it("renders the same structural primitives for a built-in word", async () => {
    await openBuiltInHvorPage()
    const builtIn = describeWordPageLayout("hvor")
    expect(builtIn).toEqual({
      hasTopHeading: true,
      hasScopeCard: true,
      cardLemma: "hvor",
      hasCardBadges: true,
      hasPinnedHomeChip: true,
      hasVerificationTrigger: true,
      hasAudioButton: true,
    })
  })

  it("renders the Danish lemma inside the synthetic root card AND at the top heading for saved words", async () => {
    await openSavedBogPage()
    const heading = screen.getByRole("heading", { level: 2, name: /^bog$/i })
    expect(heading.closest('[data-testid="wordbank-lemma-scope-card"]')).toBeNull()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).getByTestId("wordbank-lemma-card-lemma")).toHaveTextContent(/^bog$/)
  })

  it("renders the Danish lemma inside the synthetic root card AND at the top heading for built-in words", async () => {
    await openBuiltInHvorPage()
    const heading = screen.getByRole("heading", { level: 2, name: /^hvor$/i })
    expect(heading.closest('[data-testid="wordbank-lemma-scope-card"]')).toBeNull()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).getByTestId("wordbank-lemma-card-lemma")).toHaveTextContent(/^hvor$/)
  })

  it("renders pinned-home chips inside the synthetic root card for built-in words", async () => {
    await openBuiltInHvorPage()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).getByTestId("wordbank-pinned-home-card")).toHaveTextContent("Pronouns: Question Words")
  })

  it("shows the verification trigger as Verified for built-in/presaved words", async () => {
    const user = await openBuiltInHvorPage()
    await user.click(screen.getByRole("button", { name: /verification/i }))
    const popover = await screen.findByTestId("wordbank-verification-popover")
    expect(within(popover).getByText(/^Verified$/i)).toBeInTheDocument()
  })

  it("renders exactly one pronunciation button (top heading), not duplicated inside the card", async () => {
    await openSavedBogPage()
    expect(screen.getAllByRole("button", { name: /listen to bog/i })).toHaveLength(1)
  })
})

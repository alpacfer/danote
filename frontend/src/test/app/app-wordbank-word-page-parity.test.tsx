import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, within } from "@/test/app-test-helpers"
import userEvent from "@testing-library/user-event"

// Locks in the shared specimen contract for saved and built-in word pages.
describe("App wordbank word-page parity", () => {
  function savedBogResponse() {
    return {
      lemma: "bog",
      english_translation: "book",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      is_sectioned: false,
      categories: ["Furniture"],
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
          page_id: "hv_questions",
          page_title: "HV Questions",
          tab_id: "hv_place_time_manner",
          tab_title: "Place, Time, Manner & Reason",
          sentinel: "__pinned_hv_questions_place_time_manner",
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
    fireEvent.click(await screen.findByRole("button", { name: /open hv questions reference/i }))
    fireEvent.click(await screen.findByRole("button", { name: /open hvor in wordbank/i }))
    await screen.findByRole("heading", { name: /^hvor$/i })
    return user
  }

  function describeWordPageLayout(lemma: string) {
    const heading = screen.getByRole("heading", { level: 2, name: new RegExp(`^${lemma}$`, "i") })
    const specimenHero = heading.closest("#wordbank-lemma-header")
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    const heroBadges = specimenHero?.querySelector('[data-testid="wordbank-lemma-header-badges"]') ?? null
    const cardPinnedHome = within(scopeCard).queryByTestId("wordbank-pinned-home-card")
    const verificationButton = screen.getByRole("button", { name: /verification/i })
    const audioButton = screen.queryByRole("button", { name: new RegExp(`listen to ${lemma}`, "i") })

    return {
      hasSpecimenHero: Boolean(specimenHero),
      hasScopeCard: Boolean(scopeCard),
      scopeRepeatsLemma: Boolean(within(scopeCard).queryByTestId("wordbank-lemma-card-lemma")),
      hasHeroBadges: Boolean(heroBadges),
      hasPinnedHomeChip: Boolean(cardPinnedHome),
      hasVerificationTrigger: Boolean(verificationButton),
      hasAudioButton: Boolean(audioButton),
    }
  }

  it("renders the same structural primitives for a saved word", async () => {
    await openSavedBogPage()
    const saved = describeWordPageLayout("bog")
    expect(saved).toEqual({
      hasSpecimenHero: true,
      hasScopeCard: true,
      scopeRepeatsLemma: false,
      hasHeroBadges: true,
      hasPinnedHomeChip: false,
      hasVerificationTrigger: true,
      hasAudioButton: true,
    })
  })

  it("renders the same structural primitives for a built-in word", async () => {
    await openBuiltInHvorPage()
    const builtIn = describeWordPageLayout("hvor")
    expect(builtIn).toEqual({
      hasSpecimenHero: true,
      hasScopeCard: true,
      scopeRepeatsLemma: false,
      hasHeroBadges: true,
      hasPinnedHomeChip: false,
      hasVerificationTrigger: true,
      hasAudioButton: true,
    })
  })

  it("renders the Danish lemma once in the specimen hero for saved words", async () => {
    await openSavedBogPage()
    const heading = screen.getByRole("heading", { level: 2, name: /^bog$/i })
    expect(heading.closest("#wordbank-lemma-header")).toBeInTheDocument()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).queryByTestId("wordbank-lemma-card-lemma")).not.toBeInTheDocument()
  })

  it("renders the Danish lemma once in the specimen hero for built-in words", async () => {
    await openBuiltInHvorPage()
    const heading = screen.getByRole("heading", { level: 2, name: /^hvor$/i })
    expect(heading.closest("#wordbank-lemma-header")).toBeInTheDocument()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).queryByTestId("wordbank-lemma-card-lemma")).not.toBeInTheDocument()
  })

  it("no longer renders pinned-home chips for built-in words — the POS badge handles that navigation", async () => {
    await openBuiltInHvorPage()
    const scopeCard = screen.getByTestId("wordbank-lemma-scope-card")
    expect(within(scopeCard).queryByTestId("wordbank-pinned-home-card")).not.toBeInTheDocument()
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

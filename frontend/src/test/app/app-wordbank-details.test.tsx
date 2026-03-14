import { fireEvent, mockFetchImplementation, renderApp, screen } from "@/test/app-test-helpers"
import {
  bogHomographWordPageContractFixture,
  cloneContractFixture,
  morHomographWordPageContractFixture,
} from "@/test/app/wordbank-contract-fixtures"

describe("App wordbank", () => {
  it("renderer-only: shows saved lemmas in wordbank and opens the word page", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [
          { lemma: "bog", variation_count: 2 },
          { lemma: "hus", variation_count: 1 },
        ],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing",
            surface_forms: [
              { form: "bogen", has_pronunciation: true },
              { form: "bogens", has_pronunciation: false },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    const bogItem = await screen.findByRole("button", { name: /bog/i })
    expect(bogItem).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /hus/i })).toBeInTheDocument()

    fireEvent.click(bogItem)
    expect(await screen.findByText(/^bog$/i)).toBeInTheDocument()
    expect((await screen.findAllByText(/^book$/i)).length).toBeGreaterThan(0)
    expect(screen.getByText(/^bogens$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^book's$/i)).not.toBeInTheDocument()
  }, 10_000)

  it("renderer-only: non-verb word pages render meaning sections and remove duplicated top metadata", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2 }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "book",
            gloss: "book",
            english_translation: "book",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            surface_forms: [{ form: "bogen", has_pronunciation: true }],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByText(/^bog$/i)).toBeInTheDocument()
    expect(screen.getAllByText(/^book$/i)).toHaveLength(1)
    expect(screen.getAllByText(/^n-word$/i)).toHaveLength(1)
  })

  it("renderer-only: meaning-section surface forms show badges without rendering surface translations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "lærer",
        english_translation: "teacher",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "teacher",
            gloss: "teacher",
            english_translation: "teacher",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            surface_forms: [
              {
                form: "lærere",
                gloss: "teacher",
                gloss_translation: "teacher",
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Plur|Definite=Ind",
                gram_raw: "sb.fk.pl.ubest",
                has_pronunciation: false,
              },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    expect(screen.queryByTestId("wordbank-lemma-header-badges")).not.toBeInTheDocument()
    expect(screen.getByText(/^lærere$/i)).toBeInTheDocument()
    expect(screen.getAllByText(/^teacher$/i)).toHaveLength(1)
    expect(screen.getByText(/^Plural$/i)).toBeInTheDocument()
  })

  it("contract-backed: word page renders translation comma gloss translation when the backend supplies both", async () => {
    const singleMeaningFixture = cloneContractFixture(bogHomographWordPageContractFixture)
    const firstMeaningSection = singleMeaningFixture.meaning_sections?.[0]
    if (!firstMeaningSection) {
      throw new Error("Expected bog contract fixture to include at least one meaning section.")
    }
    singleMeaningFixture.meaning_sections = [firstMeaningSection]

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 0 }],
      },
      lemmaDetailsResponse: singleMeaningFixture,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.getByText(/^book, for reading$/i)).toBeInTheDocument()
  })

  it("contract-backed: word page renders translated gloss text instead of the raw Danish gloss", async () => {
    const singleMeaningFixture = cloneContractFixture(bogHomographWordPageContractFixture)
    const firstMeaningSection = singleMeaningFixture.meaning_sections?.[0]
    if (!firstMeaningSection) {
      throw new Error("Expected bog contract fixture to include at least one meaning section.")
    }
    singleMeaningFixture.meaning_sections = [firstMeaningSection]

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: singleMeaningFixture,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.getByText(/^book, for reading$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^book, til læsning$/i)).not.toBeInTheDocument()
  })

  it("contract-backed: word page shows translation comma gloss translation for each homograph meaning", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 2 }],
      },
      lemmaDetailsResponse: cloneContractFixture(bogHomographWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    expect(screen.getByText(/^book, for reading$/i)).toBeInTheDocument()
    expect(screen.getByText(/^beechmast, fruit from a beech tree$/i)).toBeInTheDocument()
  })

  it("contract-backed: word page keeps the translation and uses the gloss only as disambiguation context", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "mor", variation_count: 2 }],
      },
      lemmaDetailsResponse: cloneContractFixture(morHomographWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /mor/i }))

    expect(await screen.findByRole("heading", { name: /^mor$/i })).toBeInTheDocument()
    expect(screen.getByText(/^mother, person$/i)).toBeInTheDocument()
    expect(screen.getByText(/^mother, soil layer$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^person$/i)).not.toBeInTheDocument()
  })

  it("renderer-only: verb word pages keep flat variation layout without surface translations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lære", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "lære",
        english_translation: "learn",
        is_sectioned: false,
        pos_tag: "VERB",
        morphology: "VerbForm=Inf",
        surface_forms: [{ form: "lærer", pos_tag: "VERB", morphology: "Tense=Pres|VerbForm=Fin" }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lære/i }))

    expect(await screen.findByText(/^learn$/i)).toBeInTheDocument()
    expect(screen.getByText(/^lærer$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^learns$/i)).not.toBeInTheDocument()
  })
})

import { fireEvent, mockFetchImplementation, renderApp, responseOf, screen, waitFor, within } from "@/test/app-test-helpers"
import type { LemmaDetailsResponse } from "@/app/core"
import {
  bogHomographWordPageContractFixture,
  bogVariationGlossWordPageContractFixture,
  cloneContractFixture,
  morHomographWordPageContractFixture,
  teacherSectionedWordPageContractFixture,
} from "@/test/app/wordbank-contract-fixtures"

function expectToAppearBefore(first: HTMLElement, second: HTMLElement) {
  expect(first.compareDocumentPosition(second) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
}

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
    expect((await screen.findAllByText(/^bog$/i)).length).toBeGreaterThan(0)
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

    expect((await screen.findAllByText(/^bog$/i)).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/^book$/i)).toHaveLength(1)
    const meaningBadges = screen.getByTestId("wordbank-meaning-badges-1")
    expect(within(meaningBadges).getByText(/^Noun$/i)).toBeInTheDocument()
    expect(within(meaningBadges).getByText(/^n-word$/i)).toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Singular$/i)).not.toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Indefinite$/i)).not.toBeInTheDocument()
  })

  it("renderer-only: sectioned pinned words keep pinned links inside the matching meaning card", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "en", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "en",
        english_translation: null,
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "article",
            english_translation: "a / an",
            pos_tag: "DET",
            morphology: "Gender=Com|Number=Sing",
            reference_links: [{
              page_id: "function_words",
              page_title: "Function Words",
              tab_id: "articles",
              tab_title: "Articles",
              sentinel: "__pinned_function_words_articles",
            }],
            surface_forms: [],
          },
          {
            id: 2,
            meaning_key: "number",
            english_translation: "one",
            pos_tag: "NUM",
            reference_links: [{
              page_id: "numbers_time",
              page_title: "Numbers & Time",
              tab_id: "cardinal_numbers",
              tab_title: "Cardinal Numbers",
              sentinel: "__pinned_numbers_time_cardinal_numbers",
            }],
            surface_forms: [],
          },
        ],
        surface_forms: [{ form: "en", has_pronunciation: true }],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /^en/i }))

    expect(screen.queryByTestId("wordbank-pinned-home-card")).not.toBeInTheDocument()
    expect(within(await screen.findByTestId("wordbank-meaning-pinned-links-1")).getByText("Function Words: Articles")).toBeInTheDocument()
    expect(within(await screen.findByTestId("wordbank-meaning-pinned-links-2")).getByText("Numbers & Time: Cardinal Numbers")).toBeInTheDocument()
  }, 10_000)

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

  it("renderer-only: non-sectioned word pages render additional root translations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lege", variation_count: 0 }],
      },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (url.endsWith("/api/wordbank/lemmas/lege")) {
          return responseOf({
            lemma: "lege",
            english_translation: null,
            additional_translations: ["frolic", "play"],
            is_sectioned: false,
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            surface_forms: [],
          })
        }
        throw new Error(`Unexpected lemma details request: ${url}`)
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))

    fireEvent.click(await screen.findByRole("button", { name: /lege/i }))
    expect(await screen.findByText(/^frolic, play$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^also:/i)).not.toBeInTheDocument()
  })

  it("renderer-only: sectioned meaning cards render additional meaning translations", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "fader", variation_count: 1 }],
      },
      lemmaDetailsHandler: async (input) => {
        const url = String(input)
        if (url.endsWith("/api/wordbank/lemmas/fader")) {
          return responseOf({
            lemma: "fader",
            english_translation: null,
            is_sectioned: true,
            meaning_sections: [
              {
                id: 1,
                meaning_key: "father",
                gloss: "father",
                english_translation: "father",
                additional_translations: ["dad"],
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Ind",
                surface_forms: [{ form: "far", has_pronunciation: false }],
              },
            ],
            surface_forms: [],
          })
        }
        throw new Error(`Unexpected lemma details request: ${url}`)
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))

    fireEvent.click(await screen.findByRole("button", { name: /fader/i }))
    expect(await screen.findByText(/^father, dad$/i)).toBeInTheDocument()
  })

  it("renderer-only: pronunciation triggers do not show click-to-listen tooltips", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const listenButton = await screen.findByRole("button", { name: /^listen to bog$/i })
    fireEvent.focus(listenButton)

    expect(document.querySelector("[data-slot='tooltip-content']")).not.toBeInTheDocument()
  })

  it("renderer-only: sectioned adjective cards summarize POS while the table carries variation details", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "orange", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "orange",
        english_translation: "orange",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "orange",
            gloss: "orange",
            english_translation: "orange",
            pos_tag: "ADJ",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            gram_raw: "adj. sg. ubest. fk | adj. sg. ubest. itk | adj. sg. best | adj. pl",
            surface_forms: [],
          },
        ],
        surface_forms: [
          {
            form: "orange",
            pos_tag: "ADJ",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            gram_raw: "adj. sg. ubest. fk | adj. sg. ubest. itk | adj. sg. best | adj. pl",
            has_pronunciation: false,
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /orange/i }))

    expect(await screen.findByRole("heading", { name: /^orange$/i })).toBeInTheDocument()
    const meaningCard = screen.getByTestId("wordbank-meaning-card-1")
    const table = within(meaningCard).getByRole("table")
    expect(within(table).getByText(/^singular$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^plural$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^definite$/i)).toBeInTheDocument()
    const meaningBadges = within(meaningCard).getByTestId("wordbank-meaning-badges-1")
    expect(within(meaningBadges).getByText(/^Adjective$/i)).toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^n-word$/i)).not.toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^t-word$/i)).not.toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Singular$/i)).not.toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Indefinite$/i)).not.toBeInTheDocument()
  })

  it("renderer-only: sectioned meaning cards inherit pronunciation availability from hidden lemma rows", async () => {
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
            surface_forms: [],
          },
        ],
        surface_forms: [
          {
            form: "lærer",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            has_pronunciation: true,
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    const cardListenButton = within(meaningCard).getByRole("button", { name: /^listen to lærer$/i })
    const icon = cardListenButton.querySelector("svg")
    expect(icon).not.toHaveClass("opacity-30")
  })

  it("contract-backed: sectioned word page shows right-aligned meaning category badges on the meaning card", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsResponse: cloneContractFixture(teacherSectionedWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    const categoryContainer = screen.getByTestId("wordbank-meaning-badges-1")
    expect(categoryContainer).toHaveTextContent("People")
    expect(categoryContainer).toHaveTextContent("School")
    expect(categoryContainer).toHaveTextContent("Work")
  })

  it("contract-backed: word page renders linked sentence cards without nested token cards", async () => {
    const linkedSentenceFixture: LemmaDetailsResponse = cloneContractFixture(teacherSectionedWordPageContractFixture)
    linkedSentenceFixture.linked_sentences = [
      {
        id: 41,
        source_text: "Læreren hjælper lærere",
        english_translation: "the teacher helps teachers",
        created_at: "2026-04-10T12:00:00.000Z",
        matched_token_indexes: [0, 2],
        tokens: [
          {
            token_index: 0,
            surface_form: "Læreren",
            stored_lemma: "lærer",
            lexeme_id: 8,
            meaning_id: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Def",
            gloss: "teacher",
            english_translation: "teacher",
            gloss_translation: "teacher",
          },
          {
            token_index: 1,
            surface_form: "hjælper",
            stored_lemma: "hjælpe",
            lexeme_id: 9,
            meaning_id: null,
            pos_tag: "VERB",
            morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
            gloss: null,
            english_translation: "help",
            gloss_translation: null,
          },
          {
            token_index: 2,
            surface_form: "lærere",
            stored_lemma: "lærer",
            lexeme_id: 8,
            meaning_id: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Plur|Definite=Ind",
            gloss: "teacher",
            english_translation: "teacher",
            gloss_translation: "teacher",
          },
        ],
      },
    ]

    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsResponse: linkedSentenceFixture,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()
    expect(screen.getByRole("heading", { name: /sentences/i })).toBeInTheDocument()
    const sentenceCard = screen
      .getByText((_, element) => element?.textContent === "Læreren hjælper lærere")
      .closest("[data-slot='card']")
    expect(sentenceCard).toBeTruthy()
    expect(
      Array.from((sentenceCard as HTMLElement).querySelectorAll("span.underline")).map((element) => element.textContent),
    ).toEqual(["Læreren", "lærere"])
    expect(screen.getByText(/the teacher helps teachers/i)).toBeInTheDocument()
    expect(within(sentenceCard as HTMLElement).queryByRole("button")).not.toBeInTheDocument()
  })

  it("contract-backed: clicking linked sentence in word page opens sentencebank sentence page", async () => {
    const linkedSentenceFixture: LemmaDetailsResponse = cloneContractFixture(teacherSectionedWordPageContractFixture)
    linkedSentenceFixture.linked_sentences = [
      {
        id: 41,
        source_text: "Læreren hjælper lærere",
        english_translation: "the teacher helps teachers",
        created_at: "2026-04-10T12:00:00.000Z",
        matched_token_indexes: [0],
        tokens: [
          {
            token_index: 0,
            surface_form: "Læreren",
            stored_lemma: "lærer",
            lexeme_id: 8,
            meaning_id: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Def",
            gloss: "teacher",
            english_translation: "teacher",
            gloss_translation: "teacher",
          },
        ],
      },
    ]

    mockFetchImplementation({
      sentencebankResponse: {
        items: [
          {
            id: 41,
            source_text: "Læreren hjælper lærere",
            english_translation: "the teacher helps teachers",
            created_at: "2026-04-10T12:00:00.000Z",
            tokens: [
              {
                token_index: 0,
                surface_form: "Læreren",
                stored_lemma: "lærer",
                lexeme_id: 8,
                meaning_id: 1,
                pos_tag: "NOUN",
                morphology: "Gender=Com|Number=Sing|Definite=Def",
                english_translation: "teacher",
                gloss_translation: "teacher",
              },
            ],
          },
        ],
      },
      lemmasResponse: {
        items: [{ lemma: "lærer", variation_count: 1 }],
      },
      lemmaDetailsResponse: linkedSentenceFixture,
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /lærer/i }))

    expect(await screen.findByRole("heading", { name: /^lærer$/i })).toBeInTheDocument()

    // click linked sentence → navigate to sentencebank sentence page
    fireEvent.click(screen.getByRole("button", { name: /Læreren hjælper lærere/i }))

    // now in sentencebank sentence page — token card visible
    expect((await screen.findAllByRole("button", { name: /Læreren/i })).length).toBeGreaterThan(0)
  })

  it("renderer-only: word page loading uses the final root word-card skeleton layout", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsHandler: async () => new Promise<Response>(() => {}),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    await waitFor(
      () => {
        expect(screen.getByTestId("wordbank-details-loading-skeleton")).toBeInTheDocument()
      },
      { timeout: 1000 },
    )
    const loadingCards = screen.getAllByTestId("wordbank-details-loading-card")
    expect(loadingCards).toHaveLength(1)
    expect(loadingCards[0]).toHaveClass("md:w-1/2")
  })

  it("renderer-only: word page loading uses the final sectioned skeleton layout for direct meaning opens", async () => {
    mockFetchImplementation({
      lemmasResponse: { items: [] },
      searchWordbankResponse: {
        items: [
          {
            lemma: "mor",
            display_lemma: "mor",
            meaning_id: 2,
            meaning_key: "person",
            gloss: "person",
            gloss_translation: "person",
            variation_count: 1,
            english_translation: "mother",
            match_surface: null,
            query_cor_ids: [],
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
          },
        ],
      },
      corSearchFormResponse: {
        form: "mor",
        groups: [],
      },
      lemmaDetailsHandler: async () => new Promise<Response>(() => {}),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /search/i }))
    const commandDialog = await screen.findByRole("dialog")
    fireEvent.change(within(commandDialog).getByPlaceholderText(/search words/i), { target: { value: "mor" } })
    fireEvent.click(await within(commandDialog).findByText(/^mor$/i, { selector: "strong" }))

    await waitFor(
      () => {
         expect(screen.getByTestId("wordbank-details-loading-skeleton")).toBeInTheDocument()
      },
      { timeout: 1000 },
    )
    const loadingCards = screen.getAllByTestId("wordbank-details-loading-card")
    expect(loadingCards).toHaveLength(2)
    expect(loadingCards[0]).not.toHaveClass("md:w-1/2")
  })

  it("contract-backed: word page renders translation with gloss translation when the backend supplies both", async () => {
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
    expect(screen.getByText(/^book \(for reading\)$/i)).toBeInTheDocument()
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
    expect(screen.getByText(/^book \(for reading\)$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^book, til læsning$/i)).not.toBeInTheDocument()
  })

  it("contract-backed: word page shows translation with gloss translation for each homograph meaning", async () => {
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
    expect(screen.getByText(/^book \(for reading\)$/i)).toBeInTheDocument()
    expect(screen.getByText(/^beechmast \(fruit from a beech tree\)$/i)).toBeInTheDocument()
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
    expect(screen.getByText(/^mother \(person\)$/i)).toBeInTheDocument()
    expect(screen.getByText(/^mother \(soil layer\)$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^person$/i)).not.toBeInTheDocument()
  })

  it("contract-backed: non-sectioned word page shows root category badges in the header", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 1 }],
      },
      lemmaDetailsResponse: cloneContractFixture(bogVariationGlossWordPageContractFixture),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    expect(await screen.findByRole("heading", { name: /^bog$/i })).toBeInTheDocument()
    const categoryContainer = screen.getByTestId("wordbank-lemma-header-badges")
    expect(categoryContainer).toHaveTextContent("Food")
    expect(categoryContainer).toHaveTextContent("Household Objects")
    expect(screen.queryByText(/^book's$/i)).not.toBeInTheDocument()
  })

  it("renderer-only: verb word pages render the shared paradigm table from the first saved slot", async () => {
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
    const headerBadges = screen.getByTestId("wordbank-lemma-header-badges")
    expect(within(headerBadges).getByText(/^Verb$/i)).toBeInTheDocument()
    expect(within(headerBadges).queryByText(/^Infinitive$/i)).not.toBeInTheDocument()
    expect(within(headerBadges).queryByText(/^Active$/i)).not.toBeInTheDocument()
    const table = screen.getByRole("table")
    expect(within(table).getByText(/^infinitive$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^present$/i)).toBeInTheDocument()
    expect(within(table).queryByText(/^form$/i)).not.toBeInTheDocument()
    expect(screen.getByText(/^lærer$/i)).toBeInTheDocument()
    expect(screen.queryByText(/^learns$/i)).not.toBeInTheDocument()
  })

  it("renderer-only: sectioned verb pages place one saved form into multiple verb rows when gram_raw covers both", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "komme", variation_count: 1 }],
      },
      lemmaDetailsResponse: {
        lemma: "komme",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "come",
            gloss: "come",
            english_translation: "come",
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            gram_raw: "vb.inf.akt",
            surface_forms: [
              {
                form: "kom",
                pos_tag: "VERB",
                morphology: "Tense=Past|VerbForm=Fin",
                gram_raw: "vb.præt.akt | vb.imp",
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
    fireEvent.click(await screen.findByRole("button", { name: /komme/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    expect(within(meaningCard).getByText(/^at komme$/i)).toBeInTheDocument()
    expect(within(meaningCard).queryByText(/^1$/)).not.toBeInTheDocument()
    const meaningBadges = within(meaningCard).getByTestId("wordbank-meaning-badges-1")
    expect(within(meaningBadges).getByText(/^Verb$/i)).toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Infinitive$/i)).not.toBeInTheDocument()
    expect(within(meaningBadges).queryByText(/^Active$/i)).not.toBeInTheDocument()
    const table = within(meaningCard).getByRole("table")
    expect(within(table).getByText(/^past$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^imperative$/i)).toBeInTheDocument()
    expect(within(table).queryByText(/^form$/i)).not.toBeInTheDocument()
    expect(within(meaningCard).getAllByText(/^kom$/i).length).toBeGreaterThanOrEqual(2)
  })

  it("renderer-only: sectioned verb pages do not duplicate the infinitive when surface_forms repeats the lemma", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "stige", variation_count: 4 }],
      },
      lemmaDetailsResponse: {
        lemma: "stige",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "rise",
            gloss: "rise",
            english_translation: "to rise",
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            surface_forms: [
              { form: "stige", pos_tag: "VERB", morphology: "VerbForm=Inf|Voice=Act" },
              { form: "stiger", pos_tag: "VERB", morphology: "Tense=Pres|VerbForm=Fin|Voice=Act" },
              { form: "steg", pos_tag: "VERB", morphology: "Tense=Past|VerbForm=Fin|Voice=Act" },
              { form: "steget", pos_tag: "VERB", morphology: "VerbForm=Part|Voice=Act" },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /stige/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    const table = within(meaningCard).getByRole("table")
    expect(within(table).getByRole("row", { name: /^Infinitive stige$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Present stiger$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Past steg$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Past participle steget$/i })).toBeInTheDocument()
  })

  it("renderer-only: sectioned verb pages keep same-spelling lemma and past forms in separate rows", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "ville", variation_count: 2 }],
      },
      lemmaDetailsResponse: {
        lemma: "ville",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "want",
            gloss: "want",
            english_translation: "to want to",
            pos_tag: "VERB",
            morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
            surface_forms: [
              { form: "vil", pos_tag: "VERB", morphology: "Tense=Pres|VerbForm=Fin|Voice=Act" },
              { form: "ville", pos_tag: "VERB", morphology: "Tense=Past|VerbForm=Fin|Voice=Act" },
              { form: "villet", pos_tag: "VERB", morphology: "VerbForm=Part|Voice=Act" },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /ville/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    const table = within(meaningCard).getByRole("table")
    expect(within(table).getByRole("row", { name: /^Infinitive ville$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Present vil$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Past ville$/i })).toBeInTheDocument()
    expect(within(table).getByRole("row", { name: /^Past participle villet$/i })).toBeInTheDocument()
  })

  it("renderer-only: sectioned adjective word pages render the paradigm table from the initial saved slot", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "smuk", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "smuk",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "beautiful",
            gloss: "beautiful",
            english_translation: "beautiful",
            pos_tag: "ADJ",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            gram_raw: "adj.sg.ubest.fk",
            surface_forms: [],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /smuk/i }))

    const meaningCard = await screen.findByTestId("wordbank-meaning-card-1")
    const table = within(meaningCard).getByRole("table")
    expect(within(table).getByText(/^singular$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^indefinite$/i)).toBeInTheDocument()
    expect(within(meaningCard).getByText(/^n-word:$/i)).toBeInTheDocument()
  })

  it("renderer-only: non-sectioned noun word pages render the paradigm table from the initial saved slot", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bog", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "bog",
        english_translation: "book",
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        surface_forms: [
          { form: "bog", pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Ind", has_pronunciation: false },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bog/i }))

    const table = await screen.findByRole("table")
    const headerBadges = screen.getByTestId("wordbank-lemma-header-badges")
    expect(within(headerBadges).getByText(/^Noun$/i)).toBeInTheDocument()
    expect(within(headerBadges).getByText(/^n-word$/i)).toBeInTheDocument()
    expect(within(headerBadges).queryByText(/^Singular$/i)).not.toBeInTheDocument()
    expect(within(headerBadges).queryByText(/^Indefinite$/i)).not.toBeInTheDocument()
    expect(within(table).getByText(/^singular$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^plural$/i)).toBeInTheDocument()
    expect(within(table).getByText(/^definite$/i)).toBeInTheDocument()
  })

  it("renderer-only: non-COR adjective forms with partial morphology stay in the paradigm table", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "ukomfortabel", variation_count: 2 }],
      },
      lemmaDetailsResponse: {
        lemma: "ukomfortabel",
        english_translation: "uncomfortable",
        is_sectioned: false,
        pos_tag: "ADJ",
        morphology: "Degree=Pos|Gender=Com|Number=Sing",
        surface_forms: [
          { form: "ukomfortabel", pos_tag: "ADJ", morphology: "Degree=Pos|Gender=Com|Number=Sing", has_pronunciation: false },
          { form: "ukomfortabelt", pos_tag: "ADJ", morphology: "Degree=Pos|Gender=Neut|Number=Sing", has_pronunciation: false },
          { form: "ukomfortable", pos_tag: "ADJ", morphology: "Degree=Pos|Number=Plur", has_pronunciation: false },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /ukomfortabel/i }))

    const scopeCard = await screen.findByTestId("wordbank-lemma-scope-card")
    const table = within(scopeCard).getByRole("table")
    expect(within(table).getByRole("button", { name: /^listen to ukomfortabelt$/i })).toBeInTheDocument()
    expect(within(table).getAllByRole("button", { name: /^listen to ukomfortable$/i })).toHaveLength(2)
    expect(within(scopeCard).queryByText(/other forms/i)).not.toBeInTheDocument()
  })

  it("renderer-only: non-COR singular definite adjective forms fill the shared plural slots", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "ukomfortabel", variation_count: 2 }],
      },
      lemmaDetailsResponse: {
        lemma: "ukomfortabel",
        english_translation: "uncomfortable",
        is_sectioned: false,
        pos_tag: "ADJ",
        morphology: "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
        surface_forms: [
          {
            form: "ukomfortabel",
            pos_tag: "ADJ",
            morphology: "Degree=Pos|Gender=Com|Number=Sing|Definite=Ind",
            has_pronunciation: false,
          },
          {
            form: "ukomfortabelt",
            pos_tag: "ADJ",
            morphology: "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
            has_pronunciation: false,
          },
          {
            form: "ukomfortable",
            pos_tag: "ADJ",
            morphology: "Degree=Pos|Number=Sing|Definite=Def",
            has_pronunciation: false,
          },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /ukomfortabel/i }))

    const scopeCard = await screen.findByTestId("wordbank-lemma-scope-card")
    const table = within(scopeCard).getByRole("table")
    expect(within(table).getAllByRole("button", { name: /^listen to ukomfortable$/i })).toHaveLength(3)
  })

  it("renderer-only: non-sectioned word pages keep the paradigm table inside the scope card", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "bad", variation_count: 0 }],
      },
      lemmaDetailsResponse: {
        lemma: "bad",
        english_translation: "bath",
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Gender=Neut|Number=Sing|Definite=Ind",
        surface_forms: [
          { form: "bad", pos_tag: "NOUN", morphology: "Gender=Neut|Number=Sing|Definite=Ind", has_pronunciation: false },
          { form: "badet", pos_tag: "NOUN", morphology: "Gender=Neut|Number=Sing|Definite=Def", has_pronunciation: false },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /bad/i }))

    const scopeCard = await screen.findByTestId("wordbank-lemma-scope-card")
    expect(await screen.findByRole("heading", { name: /^bad$/i })).toBeInTheDocument()
    expect(within(scopeCard).queryByRole("heading", { name: /^bad$/i })).not.toBeInTheDocument()
    expect(within(scopeCard).getByRole("table")).toBeInTheDocument()
  })

  it("renderer-only: sectioned noun word pages render irregular variations before the standard noun slots", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "fader", variation_count: 4 }],
      },
      lemmaDetailsResponse: {
        lemma: "fader",
        is_sectioned: true,
        meaning_sections: [
          {
            id: 1,
            meaning_key: "father",
            gloss: "father",
            english_translation: "father",
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            surface_forms: [
              { form: "far", pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Ind", has_pronunciation: false },
              { form: "faderen", pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Def", has_pronunciation: false },
              { form: "fædre", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Ind", has_pronunciation: false },
              { form: "fædrene", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Def", has_pronunciation: false },
            ],
          },
        ],
        surface_forms: [],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /fader/i }))

    const far = await screen.findByText(/^far$/i)
    const faderen = screen.getByText(/^faderen$/i)
    const fædre = screen.getByText(/^fædre$/i)
    const fædrene = screen.getByText(/^fædrene$/i)

    expectToAppearBefore(far, faderen)
    expectToAppearBefore(faderen, fædre)
    expectToAppearBefore(fædre, fædrene)
  })

  it("renderer-only: flat variation cards render irregular variations before the standard noun slots", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "fader", variation_count: 4 }],
      },
      lemmaDetailsResponse: {
        lemma: "fader",
        english_translation: "father",
        is_sectioned: false,
        pos_tag: "NOUN",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        surface_forms: [
          { form: "far", pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Ind", has_pronunciation: false },
          { form: "faderen", pos_tag: "NOUN", morphology: "Gender=Com|Number=Sing|Definite=Def", has_pronunciation: false },
          { form: "fædre", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Ind", has_pronunciation: false },
          { form: "fædrene", pos_tag: "NOUN", morphology: "Gender=Com|Number=Plur|Definite=Def", has_pronunciation: false },
        ],
      },
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")
    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /fader/i }))

    const far = await screen.findByText(/^far$/i)
    const faderen = screen.getByText(/^faderen$/i)
    const fædre = screen.getByText(/^fædre$/i)
    const fædrene = screen.getByText(/^fædrene$/i)

    expectToAppearBefore(far, faderen)
    expectToAppearBefore(faderen, fædre)
    expectToAppearBefore(fædre, fædrene)
  })
})

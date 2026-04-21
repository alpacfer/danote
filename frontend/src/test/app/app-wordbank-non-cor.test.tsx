import { fireEvent, mockFetchImplementation, renderApp, screen, within } from "@/test/app-test-helpers"

function buildNonCorLemmaDetails() {
  return {
    lemma: "superstor",
    dictionary_status: "generated_non_cor" as const,
    english_translation: null,
    is_sectioned: true,
    meaning_sections: [
      {
        id: 1,
        meaning_key: "very large",
        dictionary_status: "generated_non_cor" as const,
        gloss: "very large",
        english_translation: "super big",
        pos_tag: "ADJ",
        morphology: "Degree=Pos|Number=Sing|Definite=Ind",
        surface_forms: [
          {
            form: "superstort",
            pos_tag: "ADJ",
            morphology: "Degree=Pos|Gender=Neut|Number=Sing|Definite=Ind",
          },
        ],
      },
    ],
    related_words: {
      status: "ready" as const,
      items: [
        {
          id: 1,
          relation_type: "compound_component" as const,
          lemma: "super",
          english_translation: "super",
          pos_tag: "ADV",
          saved_match: { status: "unsaved" as const },
          display_variant: null,
          candidate_variants: [],
        },
        {
          id: 2,
          relation_type: "compound_component" as const,
          lemma: "stor",
          english_translation: "large",
          pos_tag: "ADJ",
          saved_match: { status: "unsaved" as const },
          display_variant: null,
          candidate_variants: [],
        },
      ],
    },
    surface_forms: [],
  }
}

describe("App wordbank non-COR entries", () => {
  it("renderer-only: shows Not in COR for generated entries", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "superstor", variation_count: 1 }],
      },
      lemmaDetailsResponse: buildNonCorLemmaDetails(),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /superstor/i }))

    const badges = await screen.findAllByText("Not in COR")
    expect(badges.length).toBeGreaterThan(0)
  })

  it("renderer-only: renders related decomposition items even when they have no COR variants", async () => {
    mockFetchImplementation({
      lemmasResponse: {
        items: [{ lemma: "superstor", variation_count: 1 }],
      },
      lemmaDetailsResponse: buildNonCorLemmaDetails(),
    })

    renderApp()
    await screen.findByLabelText("backend-connection-status")

    fireEvent.click(screen.getByRole("button", { name: /wordbank/i }))
    fireEvent.click(await screen.findByRole("button", { name: /superstor/i }))

    const relatedHeading = await screen.findByRole("heading", { name: /^related$/i })
    const relatedSection = relatedHeading.parentElement
    expect(relatedSection).not.toBeNull()
    const relatedScope = within(relatedSection as HTMLElement)
    expect(relatedScope.getAllByText(/^super$/i).length).toBeGreaterThan(0)
    expect(relatedScope.getByText(/^stor$/i)).toBeInTheDocument()
    expect(relatedScope.getByText(/^large$/i)).toBeInTheDocument()
  })
})

export type AnalyzeToken = {
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

export type ResolveQueryPayload = {
  query_surface: string
  query_lemma: string | null
  classification: "known" | "variation" | "typo_likely" | "uncertain" | "new"
  matched_lemma: string | null
  matched_lemma_summary: {
    lemma: string
    english_translation: string | null
    variation_count: number
  } | null
  query_pos_tag: string | null
  query_morphology: string | null
  resolved_surface: string
  resolved_lemma: string | null
  da_to_en_translation: string | null
  en_to_da_translation: string | null
  en_to_da_lemma: string | null
  en_to_da_pos_tag: string | null
  en_to_da_morphology: string | null
  query_language: "en" | "da" | "ambiguous" | null
  query_language_confidence: number | null
}

export function buildWordActionsFromResolvePayload(payload: ResolveQueryPayload) {
  if (payload.classification === "known") {
    const lemma = payload.matched_lemma_summary?.lemma ?? payload.query_lemma ?? payload.query_surface
    return [
      {
        action_type: "open_wordbank" as const,
        surface: payload.query_surface,
        lemma,
        translation_label: null,
        direction: "known" as const,
        direction_label: "Wordbank",
        pos_tag: payload.query_pos_tag,
        morphology: payload.query_morphology,
        show_lemma: false,
      },
    ]
  }

  if (payload.classification === "variation" && payload.matched_lemma_summary) {
    return [
      {
        action_type: "add_variation" as const,
        surface: payload.query_surface,
        lemma: payload.matched_lemma_summary.lemma,
        translation_label: payload.query_surface,
        direction: "variation" as const,
        direction_label: "Variation",
        pos_tag: payload.query_pos_tag,
        morphology: payload.query_morphology,
        show_lemma: false,
      },
    ]
  }

  const actions: Array<{
    action_type: "add_as_new"
    surface: string
    lemma: string
    translation_label: string | null
    direction: "da_to_en" | "en_to_da"
    direction_label: string
    pos_tag: string | null
    morphology: string | null
    show_lemma: boolean
  }> = []

  if (payload.classification === "typo_likely" && !payload.da_to_en_translation && !payload.en_to_da_translation) {
    return actions
  }

  const queryLemma = payload.query_lemma ?? payload.query_surface
  if (payload.da_to_en_translation || !payload.en_to_da_translation) {
    actions.push({
      action_type: "add_as_new",
      surface: payload.query_surface,
      lemma: queryLemma,
      translation_label: payload.da_to_en_translation ?? payload.query_surface,
      direction: "da_to_en",
      direction_label: "Danish -> English",
      pos_tag: payload.query_pos_tag,
      morphology: payload.query_morphology,
      show_lemma: payload.query_surface !== queryLemma,
    })
  }

  const enToDaLemma = payload.en_to_da_lemma ?? payload.en_to_da_translation
  if (payload.en_to_da_translation && !(payload.query_language === "da" && (payload.query_language_confidence ?? 0) >= 0.7)) {
    actions.push({
      action_type: "add_as_new",
      surface: payload.en_to_da_translation,
      lemma: enToDaLemma ?? payload.en_to_da_translation,
      translation_label: payload.en_to_da_translation,
      direction: "en_to_da",
      direction_label: "English -> Danish",
      pos_tag: payload.en_to_da_pos_tag,
      morphology: payload.en_to_da_morphology,
      show_lemma: (enToDaLemma ?? payload.en_to_da_translation) !== payload.en_to_da_translation,
    })
  }

  return actions
}

export function responseOf(payload: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => payload,
  } as Response
}

export function getNotesEditor(): HTMLElement {
  return screen.getByRole("textbox", { name: /lesson notes/i })
}

export function setNotesEditorText(value: string) {
  const input = screen.getByTestId("lesson-notes-test-input")
  fireEvent.change(input, { target: { value } })
}

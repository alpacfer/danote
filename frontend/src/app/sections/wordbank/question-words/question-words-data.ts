export const QUESTION_WORDS_SENTINEL = "__question_words"

export type QuestionWordCategory = "people_things" | "choice" | "place_time_manner_reason"

export type QuestionWordEntry = {
  lemma: string
  translation: string
  category: QuestionWordCategory
  posTag: string
  morphology: string
}

export const QUESTION_WORD_CATEGORY_LABELS: Record<QuestionWordCategory, string> = {
  people_things: "People & things",
  choice: "Choice",
  place_time_manner_reason: "Place, time, manner & reason",
}

// HV question words plus the interrogative pronouns that previously lived on
// the "Questions and More Pronouns" page. This is the single canonical home
// for all interrogative forms (hvem/hvad/hvilken/hvilket/hvilke/hvis/hvor…).
export const QUESTION_WORDS: QuestionWordEntry[] = [
  { lemma: "hvem", translation: "who", category: "people_things", posTag: "PRON", morphology: "PronType=Int" },
  { lemma: "hvad", translation: "what", category: "people_things", posTag: "PRON", morphology: "PronType=Int|Gender=Neut" },
  { lemma: "hvilken", translation: "which (common)", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Com" },
  { lemma: "hvilket", translation: "which (neuter)", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Neut" },
  { lemma: "hvilke", translation: "which (plural)", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Plur" },
  { lemma: "hvis", translation: "whose", category: "choice", posTag: "DET", morphology: "PronType=Int|Poss=Yes" },
  { lemma: "hvor", translation: "where", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvornår", translation: "when", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvordan", translation: "how", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvorfor", translation: "why", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
]

const QUESTION_WORDS_BY_LEMMA: Record<string, QuestionWordEntry> = Object.fromEntries(
  QUESTION_WORDS.map((entry) => [entry.lemma, entry]),
)

export function parseQuestionWordsSentinel(selectedLemma: string): boolean {
  return selectedLemma === QUESTION_WORDS_SENTINEL
}

export function getQuestionWordEntry(lemma: string | null | undefined): QuestionWordEntry | null {
  const normalized = (lemma ?? "").trim().toLocaleLowerCase("da-DK")
  return QUESTION_WORDS_BY_LEMMA[normalized] ?? null
}

export function isEnglishQuestionWordQuery(query: string): boolean {
  const normalized = query.trim().toLocaleLowerCase("en-US")
  return ["who", "what", "which", "whose", "where", "when", "how", "why"].includes(normalized)
}

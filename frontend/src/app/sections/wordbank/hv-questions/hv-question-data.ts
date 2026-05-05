export const HV_QUESTION_SENTINEL = "__hv_questions"

export type HvQuestionCategory = "people_things" | "choice" | "place_time_manner_reason"

export type HvQuestionEntry = {
  lemma: string
  translation: string
  category: HvQuestionCategory
  posTag: string
  morphology: string
}

export const HV_QUESTION_CATEGORY_LABELS: Record<HvQuestionCategory, string> = {
  people_things: "People and Things",
  choice: "Choice",
  place_time_manner_reason: "Place, Time, Manner and Reason",
}

export const HV_QUESTION_WORDS: HvQuestionEntry[] = [
  { lemma: "hvem", translation: "who", category: "people_things", posTag: "PRON", morphology: "PronType=Int" },
  { lemma: "hvad", translation: "what", category: "people_things", posTag: "PRON", morphology: "PronType=Int|Gender=Neut" },
  { lemma: "hvilken", translation: "which", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Com" },
  { lemma: "hvilket", translation: "which", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Neut" },
  { lemma: "hvilke", translation: "which", category: "choice", posTag: "DET", morphology: "PronType=Int|Number=Plur" },
  { lemma: "hvis", translation: "whose", category: "choice", posTag: "DET", morphology: "PronType=Int|Poss=Yes" },
  { lemma: "hvor", translation: "where", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvornår", translation: "when", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvordan", translation: "how", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
  { lemma: "hvorfor", translation: "why", category: "place_time_manner_reason", posTag: "ADV", morphology: "PronType=Int" },
]

export function parseHvQuestionSentinel(selectedLemma: string): boolean {
  return selectedLemma === HV_QUESTION_SENTINEL
}

export function getHvQuestionEntry(lemma: string | null | undefined): HvQuestionEntry | null {
  const normalized = (lemma ?? "").trim().toLocaleLowerCase("da-DK")
  return HV_QUESTION_WORDS.find((entry) => entry.lemma === normalized) ?? null
}

export function isEnglishHvQuestionQuery(query: string): boolean {
  const normalized = query.trim().toLocaleLowerCase("en-US")
  return ["who", "what", "which", "whose", "where", "when", "how", "why"].includes(normalized)
}

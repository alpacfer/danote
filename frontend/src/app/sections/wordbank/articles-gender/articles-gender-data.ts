export const ARTICLES_GENDER_SENTINEL = "__articles_gender"

export type ArticleEntry = {
  lemma: string
  english: string
  description?: string
  playForm?: string
}

export const ARTICLE_ROWS: ArticleEntry[] = [
  { lemma: "en", english: "a / an", description: "n-word" },
  { lemma: "et", english: "a / an", description: "t-word" },
  { lemma: "-en", english: "the", description: "n-word singular suffix", playForm: "en" },
  { lemma: "-et", english: "the", description: "t-word singular suffix", playForm: "et" },
  { lemma: "-ne", english: "the", description: "plural suffix" },
]

export type ArticleParadigmRow = {
  label: string
  example: string
  english: string
}

export const INDEFINITE_ARTICLE_ROWS: ArticleParadigmRow[] = [
  { label: "Common (en)", example: "en bil", english: "a car" },
  { label: "Neuter (et)", example: "et hus", english: "a house" },
]

export const DEFINITE_SUFFIX_ROWS: ArticleParadigmRow[] = [
  { label: "Common -en", example: "bilen", english: "the car" },
  { label: "Neuter -et", example: "huset", english: "the house" },
  { label: "Plural -ne", example: "bilerne / husene", english: "the cars / the houses" },
]

export type NounParadigmRow = {
  gender: "common" | "neuter"
  indefinite: string
  definite: string
  pluralIndefinite: string
  pluralDefinite: string
  english: string
}

export const NOUN_PARADIGM_ROWS: NounParadigmRow[] = [
  {
    gender: "common",
    indefinite: "en bil",
    definite: "bilen",
    pluralIndefinite: "biler",
    pluralDefinite: "bilerne",
    english: "car",
  },
  {
    gender: "neuter",
    indefinite: "et hus",
    definite: "huset",
    pluralIndefinite: "huse",
    pluralDefinite: "husene",
    english: "house",
  },
  {
    gender: "common",
    indefinite: "en dreng",
    definite: "drengen",
    pluralIndefinite: "drenge",
    pluralDefinite: "drengene",
    english: "boy",
  },
  {
    gender: "common",
    indefinite: "en kvinde",
    definite: "kvinden",
    pluralIndefinite: "kvinder",
    pluralDefinite: "kvinderne",
    english: "woman",
  },
]

export const ARTICLES_GENDER_RULES = [
  "Roughly 75% of Danish nouns are common gender (en) and 25% are neuter (et). The gender of each noun must be memorised — there is no foolproof rule.",
  "The definite article is a suffix: -en (common), -et (neuter). Plural definite is -ne (added to the plural form).",
  "Plural endings vary: -er (most common), -e, or no ending. Always learn a noun together with its gender and plural form.",
]

export function parseArticlesGenderSentinel(selectedLemma: string): boolean {
  return selectedLemma === ARTICLES_GENDER_SENTINEL
}

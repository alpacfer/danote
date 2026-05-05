// Static Danish pronoun data.
// This file is the single source of truth for which lemmas are pronouns
// and which shared page they belong to.

export type PronounCategory = "personal_possessive" | "demonstrative" | "interrogative_other"

// ─── Sentinel lemmas used as selectedLemma values ─────────────────────────────
export const PRONOUN_SENTINEL_PREFIX = "__pronouns_"
export const PRONOUN_SENTINELS: Record<PronounCategory, string> = {
  personal_possessive: `${PRONOUN_SENTINEL_PREFIX}personal_possessive`,
  demonstrative: `${PRONOUN_SENTINEL_PREFIX}demonstrative`,
  interrogative_other: `${PRONOUN_SENTINEL_PREFIX}interrogative_other`,
}

export function parsePronounSentinel(lemma: string): PronounCategory | null {
  if (!lemma.startsWith(PRONOUN_SENTINEL_PREFIX)) return null
  const cat = lemma.slice(PRONOUN_SENTINEL_PREFIX.length) as PronounCategory
  return cat in PRONOUN_SENTINELS ? cat : null
}

// ─── Category map ──────────────────────────────────────────────────────────────
// Maps each Danish pronoun lemma (lowercase) to its category.
// den/det/de appear in both personal and demonstrative contexts; we map them to
// personal_possessive because that is the most common pronoun usage.
const PRONOUN_CATEGORY_MAP: Record<string, PronounCategory> = {
  // Personal — nominative
  jeg: "personal_possessive",
  du: "personal_possessive",
  han: "personal_possessive",
  hun: "personal_possessive",
  den: "personal_possessive",
  det: "personal_possessive",
  vi: "personal_possessive",
  i: "personal_possessive", // 2nd person plural
  de: "personal_possessive",
  // Personal — accusative / oblique
  mig: "personal_possessive",
  dig: "personal_possessive",
  ham: "personal_possessive",
  hende: "personal_possessive",
  os: "personal_possessive",
  jer: "personal_possessive",
  dem: "personal_possessive",
  sig: "personal_possessive", // reflexive
  // Formal register (capital De / Dem treated the same)
  // Possessive
  min: "personal_possessive",
  mit: "personal_possessive",
  mine: "personal_possessive",
  din: "personal_possessive",
  dit: "personal_possessive",
  dine: "personal_possessive",
  hans: "personal_possessive",
  hendes: "personal_possessive",
  dens: "personal_possessive",
  dets: "personal_possessive",
  sin: "personal_possessive",
  sit: "personal_possessive",
  sine: "personal_possessive",
  vores: "personal_possessive",
  jeres: "personal_possessive",
  deres: "personal_possessive",
  // Demonstrative
  denne: "demonstrative",
  dette: "demonstrative",
  disse: "demonstrative",
  // Interrogative
  hvem: "interrogative_other",
  hvad: "interrogative_other",
  hvilken: "interrogative_other",
  hvilket: "interrogative_other",
  hvilke: "interrogative_other",
  hvis: "interrogative_other",
  // Relative
  som: "interrogative_other",
  der: "interrogative_other",
  // Indefinite
  man: "interrogative_other",
  nogen: "interrogative_other",
  noget: "interrogative_other",
  ingen: "interrogative_other",
  intet: "interrogative_other",
  alle: "interrogative_other",
  enhver: "interrogative_other",
  ethvert: "interrogative_other",
  begge: "interrogative_other",
  hinanden: "interrogative_other",
  hverandre: "interrogative_other",
}

/** Returns the PronounCategory for a lemma (case-insensitive), or null if not a pronoun. */
export function getPronounCategory(lemma: string): PronounCategory | null {
  return PRONOUN_CATEGORY_MAP[lemma.toLowerCase()] ?? null
}

export const PRONOUN_TRANSLATIONS: Record<string, string> = {
  jeg: "I",
  mig: "me",
  du: "you",
  dig: "you",
  han: "he",
  ham: "him",
  hun: "she",
  hende: "her",
  den: "it / that",
  det: "it / that",
  sig: "oneself",
  vi: "we",
  os: "us",
  i: "you",
  jer: "you",
  de: "they / those",
  dem: "them",
  min: "my",
  mit: "my",
  mine: "my",
  din: "your",
  dit: "your",
  dine: "your",
  hans: "his",
  hendes: "her",
  dens: "its",
  dets: "its",
  sin: "one's own",
  sit: "one's own",
  sine: "one's own",
  vores: "our",
  jeres: "your",
  deres: "their",
  denne: "this",
  dette: "this",
  disse: "these",
  hvem: "who",
  hvad: "what",
  hvilken: "which",
  hvilket: "which",
  hvilke: "which",
  hvis: "whose",
  som: "who / which / that",
  der: "who / which",
  man: "one / you",
  nogen: "someone / any",
  noget: "something / any",
  ingen: "no one / none",
  intet: "nothing / none",
  alle: "all / everyone",
  enhver: "each / every",
  ethvert: "each / every",
  begge: "both",
  hinanden: "each other",
  hverandre: "each other",
}

export function pronounTranslation(lemma: string): string | null {
  return PRONOUN_TRANSLATIONS[lemma.toLowerCase()] ?? null
}

const ENGLISH_PRONOUN_QUERIES = new Set([
  "i",
  "me",
  "you",
  "he",
  "him",
  "she",
  "her",
  "it",
  "oneself",
  "we",
  "us",
  "they",
  "them",
  "my",
  "your",
  "his",
  "its",
  "our",
  "their",
  "this",
  "these",
  "that",
  "those",
  "who",
  "what",
  "which",
  "whose",
  "one",
  "someone",
  "something",
  "any",
  "no one",
  "none",
  "nothing",
  "all",
  "everyone",
  "each",
  "every",
  "both",
  "each other",
])

export function isEnglishPronounQuery(query: string): boolean {
  return ENGLISH_PRONOUN_QUERIES.has(query.toLowerCase())
}

// ─── Table data ────────────────────────────────────────────────────────────────

export type PersonalPronounRow = {
  label: string
  nominative: string | null
  accusative: string
}

export type PossessivePronounRow = {
  label: string
  common: string    // fælleskon  -en form
  neuter: string    // intetkøn   -et form
  plural: string    // flertal
}

export type DemonstrativeRow = {
  label: string
  english: string
  common: string
  neuter: string
  plural: string
}

export type OtherPronounGroup = {
  heading: string
  items: Array<{ lemma: string; english: string }>
}

// Personal pronouns — rows ordered by person / number
export const PERSONAL_PRONOUN_ROWS: PersonalPronounRow[] = [
  { label: "1st sg", nominative: "jeg", accusative: "mig" },
  { label: "2nd sg", nominative: "du", accusative: "dig" },
  { label: "3rd sg (m.)", nominative: "han", accusative: "ham" },
  { label: "3rd sg (f.)", nominative: "hun", accusative: "hende" },
  { label: "3rd sg (c.)", nominative: "den", accusative: "den" },
  { label: "3rd sg (n.)", nominative: "det", accusative: "det" },
  { label: "Reflexive", nominative: null, accusative: "sig" },
  { label: "1st pl", nominative: "vi", accusative: "os" },
  { label: "2nd pl", nominative: "I", accusative: "jer" },
  { label: "3rd pl", nominative: "de", accusative: "dem" },
  { label: "Formal", nominative: "De", accusative: "Dem" },
]

// Possessive pronouns
export const POSSESSIVE_PRONOUN_ROWS: PossessivePronounRow[] = [
  { label: "1st sg", common: "min", neuter: "mit", plural: "mine" },
  { label: "2nd sg", common: "din", neuter: "dit", plural: "dine" },
  { label: "3rd sg (m.)", common: "hans", neuter: "hans", plural: "hans" },
  { label: "3rd sg (f.)", common: "hendes", neuter: "hendes", plural: "hendes" },
  { label: "3rd sg refl.", common: "sin", neuter: "sit", plural: "sine" },
  { label: "1st pl", common: "vores", neuter: "vores", plural: "vores" },
  { label: "2nd pl", common: "jeres", neuter: "jeres", plural: "jeres" },
  { label: "3rd pl", common: "deres", neuter: "deres", plural: "deres" },
]

// Demonstrative pronouns
export const DEMONSTRATIVE_ROWS: DemonstrativeRow[] = [
  { label: "Proximal", english: "this / these", common: "denne", neuter: "dette", plural: "disse" },
  { label: "Distal", english: "that / those", common: "den", neuter: "det", plural: "de" },
]

// Interrogative / relative / indefinite groups
export const OTHER_PRONOUN_GROUPS: OtherPronounGroup[] = [
  {
    heading: "Interrogative",
    items: [
      { lemma: "hvem", english: "who" },
      { lemma: "hvad", english: "what" },
      { lemma: "hvilken", english: "which (c.)" },
      { lemma: "hvilket", english: "which (n.)" },
      { lemma: "hvilke", english: "which (pl.)" },
      { lemma: "hvis", english: "whose" },
    ],
  },
  {
    heading: "Relative",
    items: [
      { lemma: "som", english: "who / which / that" },
      { lemma: "der", english: "who / which (subject)" },
    ],
  },
  {
    heading: "Indefinite",
    items: [
      { lemma: "man", english: "one / you (generic)" },
      { lemma: "nogen", english: "someone / any (c.)" },
      { lemma: "noget", english: "something / any (n.)" },
      { lemma: "ingen", english: "no one / none (c.)" },
      { lemma: "intet", english: "nothing / none (n.)" },
      { lemma: "alle", english: "all / everyone" },
      { lemma: "enhver", english: "each / every (c.)" },
      { lemma: "ethvert", english: "each / every (n.)" },
      { lemma: "begge", english: "both" },
      { lemma: "hinanden", english: "each other" },
    ],
  },
]

export const PRONOUN_CATEGORY_LABELS: Record<PronounCategory, string> = {
  personal_possessive: "Personal and Possessive Pronouns",
  demonstrative: "Demonstrative Pronouns",
  interrogative_other: "Questions and More Pronouns",
}

// All lemmas that belong to each category (used for saved-count checks)
export const PRONOUN_LEMMAS_BY_CATEGORY: Record<PronounCategory, Set<string>> = {
  personal_possessive: new Set(
    [...PERSONAL_PRONOUN_ROWS.flatMap((r) => [r.nominative, r.accusative].filter(Boolean) as string[]),
     ...POSSESSIVE_PRONOUN_ROWS.flatMap((r) => [r.common, r.neuter, r.plural])
    ].map((l) => l.toLowerCase()),
  ),
  demonstrative: new Set(
    DEMONSTRATIVE_ROWS.flatMap((r) => [r.common, r.neuter, r.plural]).map((l) => l.toLowerCase()),
  ),
  interrogative_other: new Set(
    OTHER_PRONOUN_GROUPS.flatMap((g) => g.items.map((i) => i.lemma)).map((l) => l.toLowerCase()),
  ),
}

// Static Danish pronoun data.
// This file is the single source of truth for which lemmas are pronouns
// and which pinned reference page they belong to.

export type PronounCategory =
  | "personal"
  | "possessive"
  | "demonstrative"
  | "relative"
  | "indefinite"

export const PRONOUN_SENTINELS: Record<PronounCategory, string> = {
  personal: "__pronouns_personal",
  possessive: "__pronouns_possessive",
  demonstrative: "__pronouns_demonstrative",
  relative: "__pronouns_relative",
  indefinite: "__pronouns_indefinite",
}

const SENTINEL_TO_CATEGORY: Record<string, PronounCategory> = {
  __pronouns_personal: "personal",
  __pronouns_possessive: "possessive",
  __pronouns_demonstrative: "demonstrative",
  __pronouns_relative: "relative",
  __pronouns_indefinite: "indefinite",
}

export function parsePronounSentinel(lemma: string): PronounCategory | null {
  return SENTINEL_TO_CATEGORY[lemma] ?? null
}

// ─── Category map ──────────────────────────────────────────────────────────────
// Maps each Danish pronoun lemma (lowercase) to its category. Each lemma has
// exactly one canonical home; interrogatives (hvem/hvad/hvilken/hvis) live on
// the Question Words page, not on any pronoun page.
const PRONOUN_CATEGORY_MAP: Record<string, PronounCategory> = {
  // Personal — nominative
  jeg: "personal",
  du: "personal",
  han: "personal",
  hun: "personal",
  den: "personal",
  det: "personal",
  vi: "personal",
  i: "personal", // 2nd person plural
  de: "personal",
  // Personal — accusative / oblique
  mig: "personal",
  dig: "personal",
  ham: "personal",
  hende: "personal",
  os: "personal",
  jer: "personal",
  dem: "personal",
  sig: "personal", // reflexive
  // Possessive
  min: "possessive",
  mit: "possessive",
  mine: "possessive",
  din: "possessive",
  dit: "possessive",
  dine: "possessive",
  hans: "possessive",
  hendes: "possessive",
  dens: "possessive",
  dets: "possessive",
  sin: "possessive",
  sit: "possessive",
  sine: "possessive",
  vores: "possessive",
  jeres: "possessive",
  deres: "possessive",
  // Demonstrative
  denne: "demonstrative",
  dette: "demonstrative",
  disse: "demonstrative",
  // Relative
  som: "relative",
  der: "relative",
  // Indefinite
  man: "indefinite",
  nogen: "indefinite",
  noget: "indefinite",
  ingen: "indefinite",
  intet: "indefinite",
  alle: "indefinite",
  enhver: "indefinite",
  ethvert: "indefinite",
  begge: "indefinite",
  hinanden: "indefinite",
  hverandre: "indefinite",
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
  common: string
  neuter: string
  plural: string
}

export type DemonstrativeRow = {
  label: string
  english: string
  common: string
  neuter: string
  plural: string
}

export type SimplePronounRow = {
  lemma: string
  english: string
  note?: string
}

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

export const DEMONSTRATIVE_ROWS: DemonstrativeRow[] = [
  { label: "Proximal", english: "this / these", common: "denne", neuter: "dette", plural: "disse" },
  { label: "Distal", english: "that / those", common: "den", neuter: "det", plural: "de" },
]

export const RELATIVE_PRONOUN_ROWS: SimplePronounRow[] = [
  { lemma: "som", english: "who / which / that", note: "Most common; used as subject or object." },
  { lemma: "der", english: "who / which", note: "Subject only — replaces som when the relative is the subject." },
]

export const INDEFINITE_PRONOUN_ROWS: SimplePronounRow[] = [
  { lemma: "man", english: "one / you (generic)", note: "Generic subject, like English 'you' or 'one'." },
  { lemma: "nogen", english: "someone / any", note: "Common gender." },
  { lemma: "noget", english: "something / any", note: "Neuter gender." },
  { lemma: "ingen", english: "no one / none", note: "Common gender." },
  { lemma: "intet", english: "nothing / none", note: "Neuter gender." },
  { lemma: "alle", english: "all / everyone" },
  { lemma: "enhver", english: "each / every", note: "Common gender." },
  { lemma: "ethvert", english: "each / every", note: "Neuter gender." },
  { lemma: "begge", english: "both" },
  { lemma: "hinanden", english: "each other" },
]

// All lemmas that belong to each category (used for saved-count checks)
export const PRONOUN_LEMMAS_BY_CATEGORY: Record<PronounCategory, Set<string>> = {
  personal: new Set(
    PERSONAL_PRONOUN_ROWS.flatMap((r) => [r.nominative, r.accusative].filter(Boolean) as string[]).map(
      (l) => l.toLowerCase(),
    ),
  ),
  possessive: new Set(
    POSSESSIVE_PRONOUN_ROWS.flatMap((r) => [r.common, r.neuter, r.plural]).map((l) => l.toLowerCase()),
  ),
  demonstrative: new Set(
    DEMONSTRATIVE_ROWS.flatMap((r) => [r.common, r.neuter, r.plural]).map((l) => l.toLowerCase()),
  ),
  relative: new Set(RELATIVE_PRONOUN_ROWS.map((r) => r.lemma.toLowerCase())),
  indefinite: new Set(INDEFINITE_PRONOUN_ROWS.map((r) => r.lemma.toLowerCase())),
}

import type { CorSearchBadge } from "@/app/core"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"

type RawPinnedWordMetadata = {
  posTag?: string | null
  morphology?: string | null
}

export type PinnedWordMetadata = RawPinnedWordMetadata & {
  badges: CorSearchBadge[]
}

const PERSONAL_PRONOUN_MORPHOLOGY: Record<string, string> = {
  jeg: "PronType=Prs|Case=Nom|Person=1|Number=Sing",
  mig: "PronType=Prs|Case=Acc|Person=1|Number=Sing",
  du: "PronType=Prs|Case=Nom|Person=2|Number=Sing",
  dig: "PronType=Prs|Case=Acc|Person=2|Number=Sing",
  han: "PronType=Prs|Case=Nom|Person=3|Number=Sing|Gender=Masc",
  ham: "PronType=Prs|Case=Acc|Person=3|Number=Sing|Gender=Masc",
  hun: "PronType=Prs|Case=Nom|Person=3|Number=Sing|Gender=Fem",
  hende: "PronType=Prs|Case=Acc|Person=3|Number=Sing|Gender=Fem",
  den: "PronType=Prs,Dem|Person=3|Number=Sing|Gender=Com",
  det: "PronType=Prs,Dem|Person=3|Number=Sing|Gender=Neut",
  sig: "PronType=Prs|Reflex=Yes|Person=3",
  vi: "PronType=Prs|Case=Nom|Person=1|Number=Plur",
  os: "PronType=Prs|Case=Acc|Person=1|Number=Plur",
  i: "PronType=Prs|Case=Nom|Person=2|Number=Plur",
  jer: "PronType=Prs|Case=Acc|Person=2|Number=Plur",
  de: "PronType=Prs,Dem|Case=Nom|Person=3|Number=Plur",
  dem: "PronType=Prs|Case=Acc|Person=3|Number=Plur",
}

const POSSESSIVE_PRONOUN_MORPHOLOGY: Record<string, string> = {
  min: "PronType=Prs|Poss=Yes|Person=1|Number=Sing|Gender=Com",
  mit: "PronType=Prs|Poss=Yes|Person=1|Number=Sing|Gender=Neut",
  mine: "PronType=Prs|Poss=Yes|Person=1|Number=Plur",
  din: "PronType=Prs|Poss=Yes|Person=2|Number=Sing|Gender=Com",
  dit: "PronType=Prs|Poss=Yes|Person=2|Number=Sing|Gender=Neut",
  dine: "PronType=Prs|Poss=Yes|Person=2|Number=Plur",
  hans: "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Masc",
  hendes: "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Fem",
  dens: "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Com",
  dets: "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Neut",
  sin: "PronType=Prs|Poss=Yes|Reflex=Yes|Gender=Com",
  sit: "PronType=Prs|Poss=Yes|Reflex=Yes|Gender=Neut",
  sine: "PronType=Prs|Poss=Yes|Reflex=Yes|Number=Plur",
  vores: "PronType=Prs|Poss=Yes|Person=1|Number=Plur",
  jeres: "PronType=Prs|Poss=Yes|Person=2|Number=Plur",
  deres: "PronType=Prs|Poss=Yes|Person=3|Number=Plur",
}

const OTHER_PRONOUN_MORPHOLOGY: Record<string, string> = {
  denne: "PronType=Dem|Number=Sing|Gender=Com",
  dette: "PronType=Dem|Number=Sing|Gender=Neut",
  disse: "PronType=Dem|Number=Plur",
  hvem: "PronType=Int",
  hvad: "PronType=Int|Gender=Neut",
  hvilken: "PronType=Int|Number=Sing|Gender=Com",
  hvilket: "PronType=Int|Number=Sing|Gender=Neut",
  hvilke: "PronType=Int|Number=Plur",
  hvis: "PronType=Int,Rel|Poss=Yes",
  som: "PronType=Rel",
  der: "PronType=Rel",
  man: "PronType=Ind|Person=3|Number=Sing",
  nogen: "PronType=Ind|Gender=Com",
  noget: "PronType=Ind|Gender=Neut",
  ingen: "PronType=Neg|Gender=Com",
  intet: "PronType=Neg|Gender=Neut",
  alle: "PronType=Tot|Number=Plur",
  enhver: "PronType=Tot|Gender=Com",
  ethvert: "PronType=Tot|Gender=Neut",
  begge: "PronType=Tot|Number=Plur",
  hinanden: "PronType=Rcp",
  hverandre: "PronType=Rcp",
}

const RAW_PINNED_WORD_METADATA: Record<string, RawPinnedWordMetadata> = {
  ...Object.fromEntries(
    Object.entries({
      ...PERSONAL_PRONOUN_MORPHOLOGY,
      ...POSSESSIVE_PRONOUN_MORPHOLOGY,
      ...OTHER_PRONOUN_MORPHOLOGY,
    }).map(([lemma, morphology]) => [lemma, { posTag: "PRON", morphology }]),
  ),
  hvilken: { posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Com" },
  hvilket: { posTag: "DET", morphology: "PronType=Int|Number=Sing|Gender=Neut" },
  hvilke: { posTag: "DET", morphology: "PronType=Int|Number=Plur" },
  hvis: { posTag: "DET", morphology: "PronType=Int|Poss=Yes" },
  hvor: { posTag: "ADV", morphology: "PronType=Int" },
  hvornår: { posTag: "ADV", morphology: "PronType=Int" },
  hvordan: { posTag: "ADV", morphology: "PronType=Int" },
  hvorfor: { posTag: "ADV", morphology: "PronType=Int" },
  "-en": { posTag: "DET", morphology: "Gender=Com|Number=Sing" },
  "-et": { posTag: "DET", morphology: "Gender=Neut|Number=Sing" },
  "-ne": { posTag: "DET", morphology: "Number=Plur" },
}

for (const lemma of [
  "en",
  "et",
  "nul",
  "to",
  "tre",
  "fire",
  "fem",
  "seks",
  "syv",
  "otte",
  "ni",
  "ti",
  "elleve",
  "tolv",
  "tretten",
  "fjorten",
  "femten",
  "seksten",
  "sytten",
  "atten",
  "nitten",
  "tyve",
  "tredive",
  "fyrre",
  "halvtreds",
  "tres",
  "halvfjerds",
  "firs",
  "halvfems",
  "hundrede",
]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "NUM" }
}

for (const lemma of ["første", "anden", "tredje", "fjerde", "femte", "sjette", "syvende", "ottende", "niende", "tiende", "ellevte", "tolvte", "trettende", "tyvende", "tredivte", "tusinde"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "ADJ" }
}

for (const lemma of ["i", "på", "til", "fra", "med", "af", "over", "under", "for", "om", "hos", "ved", "mod", "gennem", "efter", "før", "mellem", "uden", "indtil", "siden"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "ADP" }
}

for (const lemma of ["og", "eller", "men", "så"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "CCONJ" }
}

for (const lemma of ["at", "fordi", "når", "da", "mens", "selvom", "inden"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "SCONJ" }
}

for (const lemma of ["mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag", "januar", "februar", "marts", "april", "maj", "juni", "juli", "august", "september", "oktober", "november", "december", "forår", "sommer", "efterår", "vinter"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "NOUN" }
}

for (const lemma of ["altid", "ofte", "sjældent", "aldrig"]) {
  RAW_PINNED_WORD_METADATA[lemma] ??= { posTag: "ADV" }
}

export const PINNED_WORD_METADATA: Record<string, PinnedWordMetadata> = Object.fromEntries(
  Object.entries(RAW_PINNED_WORD_METADATA).map(([lemma, metadata]) => [
    lemma,
    {
      ...metadata,
      badges: wordPageBadgesForSavedForm({
        pos_tag: metadata.posTag ?? null,
        morphology: metadata.morphology ?? null,
      }),
    },
  ]),
)

export function metadataForPinnedWord(lemma: string): PinnedWordMetadata | null {
  return PINNED_WORD_METADATA[lemma.trim().toLocaleLowerCase("da-DK")] ?? null
}

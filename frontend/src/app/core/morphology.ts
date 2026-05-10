import {
  POPOVER_ESTIMATED_HEIGHT_PX,
  POPOVER_VIEWPORT_MARGIN_PX,
} from "@/app/core/constants"

export function preferredPopoverSide(lineTop: number, lineBottom: number): "top" | "bottom" {
  const viewportHeight = typeof window === "undefined" ? 800 : window.innerHeight
  const spaceAbove = lineTop - POPOVER_VIEWPORT_MARGIN_PX
  const spaceBelow = viewportHeight - lineBottom - POPOVER_VIEWPORT_MARGIN_PX
  if (spaceBelow >= POPOVER_ESTIMATED_HEIGHT_PX || spaceBelow >= spaceAbove) {
    return "bottom"
  }
  return "top"
}

export type NumberLabel = "Singular" | "Plural"
export function numberFromMorphology(morphology: string | null): NumberLabel | null {
  if (!morphology) return null
  if (/(^|\|)Number=Sing(\||$)/u.test(morphology)) return "Singular"
  if (/(^|\|)Number=Plur(\||$)/u.test(morphology)) return "Plural"
  return null
}

export type GenderLabel = "Common" | "Neuter" | "Masculine" | "Feminine"
export function genderFromMorphology(morphology: string | null): GenderLabel | null {
  if (!morphology) return null
  if (/(^|\|)Gender=Com(\||$)/u.test(morphology)) return "Common"
  if (/(^|\|)Gender=Neut(\||$)/u.test(morphology)) return "Neuter"
  if (/(^|\|)Gender=Masc(\||$)/u.test(morphology)) return "Masculine"
  if (/(^|\|)Gender=Fem(\||$)/u.test(morphology)) return "Feminine"
  return null
}

export type DeterminerWordType = "n-word" | "t-word"
export function determinerWordTypeFromMorphology(morphology: string | null): DeterminerWordType | null {
  if (!morphology) return null
  if (/(^|\|)Gender=Neut(\||$)/u.test(morphology)) return "t-word"
  if (/(^|\|)Gender=(Com|Masc|Fem)(\||$)/u.test(morphology)) return "n-word"
  return null
}

export type PersonLabel = "1st person" | "2nd person" | "3rd person"
export function personFromMorphology(morphology: string | null): PersonLabel | null {
  if (!morphology) return null
  if (/(^|\|)Person=1(\||$)/u.test(morphology)) return "1st person"
  if (/(^|\|)Person=2(\||$)/u.test(morphology)) return "2nd person"
  if (/(^|\|)Person=3(\||$)/u.test(morphology)) return "3rd person"
  return null
}

export type DegreeLabel = "Positive" | "Comparative" | "Superlative"
export function degreeFromMorphology(morphology: string | null): DegreeLabel | null {
  if (!morphology) return null
  if (/(^|\|)Degree=Pos(\||$)/u.test(morphology)) return "Positive"
  if (/(^|\|)Degree=Cmp(\||$)/u.test(morphology)) return "Comparative"
  if (/(^|\|)Degree=Sup(\||$)/u.test(morphology)) return "Superlative"
  return null
}

export type VerbFormLabel = "Infinitive" | "Present" | "Past" | "Past participle" | "Imperative"
export function verbFormFromMorphology(morphology: string | null): VerbFormLabel | null {
  if (!morphology) return null
  if (/(^|\|)VerbForm=Part(\||$)/u.test(morphology)) return "Past participle"
  if (/(^|\|)VerbForm=Inf(\||$)/u.test(morphology)) return "Infinitive"
  if (/(^|\|)Mood=Imp(\||$)/u.test(morphology)) return "Imperative"
  if (/(^|\|)Tense=Past(\||$)/u.test(morphology)) return "Past"
  if (/(^|\|)Tense=Pres(\||$)/u.test(morphology)) return "Present"
  return null
}

export type VoiceLabel = "Active" | "Passive"
export function voiceFromMorphology(morphology: string | null): VoiceLabel | null {
  if (!morphology) return null
  if (/(^|\|)Voice=Act(\||$)/u.test(morphology)) return "Active"
  if (/(^|\|)Voice=Pass(\||$)/u.test(morphology)) return "Passive"
  return null
}

export type DefinitenessLabel = "Indefinite" | "Definite"
export function definitenessFromMorphology(morphology: string | null): DefinitenessLabel | null {
  if (!morphology) return null
  if (/(^|\|)Definite=Ind(\||$)/u.test(morphology)) return "Indefinite"
  if (/(^|\|)Definite=Def(\||$)/u.test(morphology)) return "Definite"
  return null
}

export type CaseLabel = "Genitive"
export function caseFromMorphology(morphology: string | null): CaseLabel | null {
  if (!morphology) return null
  if (/(^|\|)Case=Gen(\||$)/u.test(morphology)) return "Genitive"
  return null
}

export type PronTypeLabel = "Personal" | "Demonstrative" | "Interrogative" | "Relative" | "Indefinite" | "Negative" | "Total" | "Reciprocal"
export function pronTypeFromMorphology(morphology: string | null): PronTypeLabel | null {
  if (!morphology) return null
  if (/(^|\|)PronType=[^|]*Prs/u.test(morphology)) return "Personal"
  if (/(^|\|)PronType=[^|]*Dem/u.test(morphology)) return "Demonstrative"
  if (/(^|\|)PronType=[^|]*Int/u.test(morphology)) return "Interrogative"
  if (/(^|\|)PronType=[^|]*Rel/u.test(morphology)) return "Relative"
  if (/(^|\|)PronType=[^|]*Ind/u.test(morphology)) return "Indefinite"
  if (/(^|\|)PronType=[^|]*Neg/u.test(morphology)) return "Negative"
  if (/(^|\|)PronType=[^|]*Tot/u.test(morphology)) return "Total"
  if (/(^|\|)PronType=[^|]*Rcp/u.test(morphology)) return "Reciprocal"
  return null
}

export type PossessionLabel = "Possessive"
export function possessionFromMorphology(morphology: string | null): PossessionLabel | null {
  if (!morphology) return null
  if (/(^|\|)Poss=Yes(\||$)/u.test(morphology)) return "Possessive"
  return null
}

export type ReflexiveLabel = "Reflexive"
export function reflexiveFromMorphology(morphology: string | null): ReflexiveLabel | null {
  if (!morphology) return null
  if (/(^|\|)Reflex=Yes(\||$)/u.test(morphology)) return "Reflexive"
  return null
}

export function posBadgeClass(posTag: string | null): string {
  if (!posTag) return ""
  const colorByPos: Record<string, string> = {
    ADJ: "bg-pink-100 text-pink-800 dark:bg-pink-900/40 dark:text-pink-200 border-transparent",
    ADP: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900/40 dark:text-cyan-200 border-transparent",
    ADV: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-200 border-transparent",
    AUX: "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-200 border-transparent",
    CCONJ: "bg-lime-100 text-lime-800 dark:bg-lime-900/40 dark:text-lime-200 border-transparent",
    DET: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200 border-transparent",
    INTJ: "bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200 border-transparent",
    NOUN: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200 border-transparent",
    NUM: "bg-violet-100 text-violet-800 dark:bg-violet-900/40 dark:text-violet-200 border-transparent",
    PART: "bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200 border-transparent",
    PRON: "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-200 border-transparent",
    PROPN: "bg-fuchsia-100 text-fuchsia-800 dark:bg-fuchsia-900/40 dark:text-fuchsia-200 border-transparent",
    PUNCT: "bg-slate-100 text-slate-800 dark:bg-slate-800 dark:text-slate-200 border-transparent",
    SCONJ: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200 border-transparent",
    SYM: "bg-stone-100 text-stone-800 dark:bg-stone-800 dark:text-stone-200 border-transparent",
    VERB: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200 border-transparent",
    X: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200 border-transparent",
  }
  return colorByPos[posTag] ?? "bg-muted text-muted-foreground border-transparent"
}

export function secondaryTagsForPos(posTag: string | null, morphology: string | null): string[] {
  const tags: string[] = []
  const pronType = pronTypeFromMorphology(morphology)
  const possession = possessionFromMorphology(morphology)
  const reflexive = reflexiveFromMorphology(morphology)
  if (posTag === "PRON" || posTag === "DET" || posTag === "ADV") {
    if (pronType) tags.push(pronType)
    if (possession) tags.push(possession)
    if (reflexive) tags.push(reflexive)
  }
  if (posTag === "VERB" || posTag === "AUX") {
    const form = verbFormFromMorphology(morphology)
    if (form) tags.push(form)
  }
  if (posTag === "NOUN") {
    const wordType = determinerWordTypeFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    const definiteness = definitenessFromMorphology(morphology)
    const caseLabel = caseFromMorphology(morphology)
    if (wordType) tags.push(wordType)
    if (number) tags.push(number)
    if (definiteness) tags.push(definiteness)
    if (caseLabel) tags.push(caseLabel)
  }
  if (posTag === "DET") {
    const gender = determinerWordTypeFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (gender) tags.push(gender)
    if (number) tags.push(number)
  }
  if (posTag === "ADJ") {
    const gender = genderFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (gender) tags.push(gender)
    if (number) tags.push(number)
  }
  if (posTag === "PRON") {
    const person = personFromMorphology(morphology)
    const number = numberFromMorphology(morphology)
    if (person) tags.push(person)
    if (number) tags.push(number)
  }
  if (posTag === "ADV") {
    const degree = degreeFromMorphology(morphology)
    if (degree) tags.push(degree)
  }
  return tags
}

export function isLowConfidencePosTag(posTag: string | null): boolean {
  return !posTag || posTag === "X"
}

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
  const baseClass = "rounded-sm border font-lexical font-semibold italic tracking-[0.025em]"
  if (!posTag) return `${baseClass} bg-material-word text-foreground border-border/80`
  const upperTag = posTag.toUpperCase()
  const colorByPos: Record<string, string> = {
    ADJ: "bg-material-related text-foreground border-brand-sky/55",
    ADP: "bg-material-word text-foreground border-accent",
    ADV: "bg-material-related text-foreground border-brand-sky/55",
    AUX: "bg-material-grammar text-foreground border-brand-clay/50",
    CCONJ: "bg-material-word text-foreground border-accent",
    DET: "bg-material-reference text-foreground border-primary/40",
    INTJ: "bg-material-discovery text-foreground border-brand-butter",
    NOUN: "bg-material-reference text-foreground border-primary/40",
    NUM: "bg-material-discovery text-foreground border-brand-butter",
    PART: "bg-material-word text-foreground border-border/80",
    PRON: "bg-material-reference text-foreground border-primary/40",
    PROPN: "bg-material-reference text-foreground border-primary/40",
    PUNCT: "bg-muted text-muted-foreground border-border/80",
    SCONJ: "bg-material-word text-foreground border-accent",
    SYM: "bg-muted text-muted-foreground border-border/80",
    VERB: "bg-material-grammar text-foreground border-brand-clay/50",
    X: "bg-muted text-muted-foreground border-border/80",
    PHRASAL_VERB: "bg-material-grammar text-foreground border-brand-clay/50",
    IDIOM: "bg-material-grammar text-foreground border-brand-clay/50",
    HV_WORD: "bg-material-related text-foreground border-brand-sky/55",
  }
  const colorClass = colorByPos[upperTag] ?? colorByPos[posTag] ?? "bg-material-word text-foreground border-border/80"
  return `${baseClass} ${colorClass}`
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

import { type CORSearchVariant } from "@/app/core/types-api"
import {
  caseFromMorphology,
  definitenessFromMorphology,
  degreeFromMorphology,
  determinerWordTypeFromMorphology,
  numberFromMorphology,
  personFromMorphology,
  secondaryTagsForPos,
  verbFormFromMorphology,
  voiceFromMorphology,
} from "@/app/core/morphology"

export const GRAM_POS_LABELS: Record<string, string> = {
  sb: "Noun",
  vb: "Verb",
  adj: "Adjective",
  adv: "Adverb",
  pron: "Pronoun",
  "præp": "Preposition",
  konj: "Conjunction",
  art: "Article",
  prop: "Proper noun",
  talord: "Numeral",
  "udråbsord": "Interjection",
  lydord: "Onomatopoeia",
  fork: "Abbreviation",
  flerord: "Multiword",
  iflerord: "Multiword part",
  "præfiks": "Prefix",
  suffiks: "Suffix",
  romertal: "Roman numeral",
  "infmærke": "Infinitive marker",
}

export const GRAM_FEATURE_LABELS: Record<string, string> = {
  fk: "n-word",
  itk: "t-word",
  sg: "Singular",
  pl: "Plural",
  ubest: "Indefinite",
  best: "Definite",
  gen: "Genitive",
  sms: "Compound form",
  "præs": "Present",
  "præt": "Past",
  inf: "Infinitive",
  imp: "Imperative",
  akt: "Active",
  pass: "Passive",
  kompar: "Comparative",
  superl: "Superlative",
  adv: "Adverbial",
}

export type CorSearchBadge = {
  label: string
  tone: "primary" | "secondary"
}

export const COR_SECONDARY_BADGE_CLASS_BY_LABEL: Record<string, string> = {
  "n-word": "bg-emerald-50 text-emerald-900 border-emerald-400 dark:bg-emerald-950/30 dark:text-emerald-200 dark:border-emerald-500",
  "t-word": "bg-teal-50 text-teal-900 border-teal-400 dark:bg-teal-950/30 dark:text-teal-200 dark:border-teal-500",
  Singular: "bg-sky-50 text-sky-900 border-sky-400 dark:bg-sky-950/30 dark:text-sky-200 dark:border-sky-500",
  Plural: "bg-indigo-50 text-indigo-900 border-indigo-400 dark:bg-indigo-950/30 dark:text-indigo-200 dark:border-indigo-500",
  Indefinite: "bg-amber-50 text-amber-900 border-amber-400 dark:bg-amber-950/30 dark:text-amber-200 dark:border-amber-500",
  Definite: "bg-yellow-50 text-yellow-900 border-yellow-400 dark:bg-yellow-950/30 dark:text-yellow-200 dark:border-yellow-500",
  Genitive: "bg-orange-50 text-orange-900 border-orange-400 dark:bg-orange-950/30 dark:text-orange-200 dark:border-orange-500",
  "Compound form": "bg-slate-50 text-slate-900 border-slate-400 dark:bg-slate-900/40 dark:text-slate-200 dark:border-slate-500",
  Present: "bg-cyan-50 text-cyan-900 border-cyan-400 dark:bg-cyan-950/30 dark:text-cyan-200 dark:border-cyan-500",
  Past: "bg-violet-50 text-violet-900 border-violet-400 dark:bg-violet-950/30 dark:text-violet-200 dark:border-violet-500",
  Infinitive: "bg-lime-50 text-lime-900 border-lime-400 dark:bg-lime-950/30 dark:text-lime-200 dark:border-lime-500",
  Imperative: "bg-red-50 text-red-900 border-red-400 dark:bg-red-950/30 dark:text-red-200 dark:border-red-500",
  Active: "bg-blue-50 text-blue-900 border-blue-400 dark:bg-blue-950/30 dark:text-blue-200 dark:border-blue-500",
  Passive: "bg-fuchsia-50 text-fuchsia-900 border-fuchsia-400 dark:bg-fuchsia-950/30 dark:text-fuchsia-200 dark:border-fuchsia-500",
  Comparative: "bg-pink-50 text-pink-900 border-pink-400 dark:bg-pink-950/30 dark:text-pink-200 dark:border-pink-500",
  Superlative: "bg-rose-50 text-rose-900 border-rose-400 dark:bg-rose-950/30 dark:text-rose-200 dark:border-rose-500",
  Adverbial: "bg-stone-50 text-stone-900 border-stone-400 dark:bg-stone-900/40 dark:text-stone-200 dark:border-stone-500",
  "Perfect participle": "bg-purple-50 text-purple-900 border-purple-400 dark:bg-purple-950/30 dark:text-purple-200 dark:border-purple-500",
}

export function corSecondaryBadgeClass(label: string): string {
  return COR_SECONDARY_BADGE_CLASS_BY_LABEL[label] ?? "bg-muted text-muted-foreground border-muted-foreground/60"
}

export const UD_POS_PRIMARY_LABELS: Record<string, string> = {
  ADJ: "Adjective",
  ADP: "Preposition",
  ADV: "Adverb",
  AUX: "Auxiliary",
  CCONJ: "Conjunction",
  DET: "Determiner",
  INTJ: "Interjection",
  NOUN: "Noun",
  NUM: "Numeral",
  PART: "Particle",
  PRON: "Pronoun",
  PROPN: "Proper noun",
  PUNCT: "Punctuation",
  SCONJ: "Subordinating conjunction",
  SYM: "Symbol",
  VERB: "Verb",
  X: "Other",
}

export function primaryPosLabel(posTag: string | null): string | null {
  if (!posTag) {
    return null
  }
  return UD_POS_PRIMARY_LABELS[posTag] ?? posTag
}

export function badgesFromGramRaw(gramRaw: string): CorSearchBadge[] {
  const normalized = gramRaw.trim().toLocaleLowerCase("da-DK")
  if (!normalized) {
    return []
  }
  const grams = normalized.split("|").map((item) => item.trim()).filter(Boolean)
  const labels: CorSearchBadge[] = []

  for (const gram of grams) {
    const rawChunks = gram.split(".").map((chunk) => chunk.trim()).filter(Boolean)
    const chunks: string[] = []
    for (let index = 0; index < rawChunks.length; index += 1) {
      const current = rawChunks[index]
      const next = rawChunks[index + 1]
      if (current === "perf" && next === "part") {
        chunks.push("perf.part")
        index += 1
        continue
      }
      chunks.push(current)
    }

    for (let index = 0; index < chunks.length; index += 1) {
      const chunk = chunks[index]
      if (index === 0) {
        const posLabel = GRAM_POS_LABELS[chunk]
        if (posLabel) {
          labels.push({ label: posLabel, tone: "primary" })
        }
        continue
      }
      if (chunk === "perf.part") {
        labels.push({ label: "Perfect participle", tone: "secondary" })
        continue
      }
      const feature = GRAM_FEATURE_LABELS[chunk]
      if (feature) {
        labels.push({ label: feature, tone: "secondary" })
      }
    }
  }

  return labels.filter((badge, index, array) => array.findIndex((candidate) => candidate.label === badge.label) === index)
}

export function lemmaDisplayForVariant(variant: CORSearchVariant): string | null {
  const lemma = variant.lemma.trim()
  if (!lemma) {
    return null
  }
  if ((variant.pos_tag ?? "").toUpperCase() === "VERB") {
    return `at ${lemma}`
  }
  return lemma
}

export function lemmaTranslationForVariant(variant: CORSearchVariant): string | null {
  const value = variant.lemma_translation?.trim()
  return value ? value : null
}

export function saveableTranslationForVariant(variant: CORSearchVariant): string | null {
  const explicitFallback = variant.saveable_translation?.trim()
  if (explicitFallback) {
    return explicitFallback
  }
  return lemmaTranslationForVariant(variant)
}

function normalizedGlossPart(value: string | null | undefined): string | null {
  const trimmed = value?.trim()
  return trimmed ? trimmed : null
}

export function englishGlossForSavedForm(form: {
  gloss?: string | null
  gloss_translation?: string | null
}): string | null {
  return normalizedGlossPart(form.gloss_translation)
}

export function lemmaTranslationWithGloss(
  lemmaTranslation: string | null | undefined,
  glossTranslation: string | null | undefined,
): string | null {
  const normalizedLemmaTranslation = normalizedGlossPart(lemmaTranslation)
  const normalizedGlossTranslation = normalizedGlossPart(glossTranslation)
  if (!normalizedLemmaTranslation) {
    return null
  }
  if (!normalizedGlossTranslation) {
    return normalizedLemmaTranslation
  }
  if (normalizedLemmaTranslation.localeCompare(normalizedGlossTranslation, "en", { sensitivity: "base" }) === 0) {
    return normalizedLemmaTranslation
  }
  return `${normalizedLemmaTranslation}, ${normalizedGlossTranslation}`
}

export function glossDisplayForVariant(variant: CORSearchVariant): string | null {
  const translation = variant.gloss_translation?.trim()
  return translation || null
}

export function lemmaDisplayForSavedForm(form: {
  form: string
  lemma?: string | null
  pos_tag?: string | null
}): string | null {
  const lemma = form.lemma?.trim()
  if (!lemma) {
    return null
  }
  if ((form.pos_tag ?? "").toUpperCase() === "VERB") {
    return `at ${lemma}`
  }
  return lemma
}

export function glossDisplayForSavedForm(form: {
  gloss?: string | null
  gloss_translation?: string | null
}): string | null {
  return englishGlossForSavedForm(form)
}

export function badgesForSavedForm(form: {
  pos_tag?: string | null
  morphology?: string | null
  gram_raw?: string | null
}): CorSearchBadge[] {
  if (form.gram_raw?.trim()) {
    return badgesFromGramRaw(form.gram_raw)
  }
  return [
    ...(form.pos_tag ? [{ label: primaryPosLabel(form.pos_tag) ?? form.pos_tag, tone: "primary" as const }] : []),
    ...savedSecondaryTagsForPos(form.pos_tag ?? null, form.morphology ?? null).map((tag) => ({
      label: tag,
      tone: "secondary" as const,
    })),
  ]
}

function savedSecondaryTagsForPos(posTag: string | null, morphology: string | null): string[] {
  if (!posTag) {
    return []
  }

  const tags: Array<string | null> = []
  const wordType = determinerWordTypeFromMorphology(morphology)
  const number = numberFromMorphology(morphology)
  const definiteness = definitenessFromMorphology(morphology)
  const caseLabel = caseFromMorphology(morphology)
  const person = personFromMorphology(morphology)
  const verbForm = verbFormFromMorphology(morphology)
  const voice = voiceFromMorphology(morphology)
  const degree = degreeFromMorphology(morphology)
  const comparableDegree = degree === "Positive" ? null : degree

  if (posTag === "VERB" || posTag === "AUX") {
    tags.push(verbForm, voice)
  }
  if (posTag === "NOUN") {
    tags.push(wordType, number, definiteness, caseLabel)
  }
  if (posTag === "DET") {
    tags.push(wordType, number, definiteness)
  }
  if (posTag === "ADJ") {
    tags.push(wordType, number, definiteness, comparableDegree)
  }
  if (posTag === "PRON") {
    tags.push(wordType, person, number, caseLabel)
  }
  if (posTag === "ADV") {
    tags.push(comparableDegree)
  }

  if (tags.length === 0) {
    return secondaryTagsForPos(posTag, morphology)
  }

  return tags.filter((tag, index, values): tag is string => Boolean(tag) && values.indexOf(tag) === index)
}

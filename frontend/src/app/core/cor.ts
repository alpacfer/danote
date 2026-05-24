import { type CORSearchVariant } from "@/app/core/types-api"
import {
  caseFromMorphology,
  definitenessFromMorphology,
  degreeFromMorphology,
  determinerWordTypeFromMorphology,
  numberFromMorphology,
  personFromMorphology,
  possessionFromMorphology,
  pronTypeFromMorphology,
  reflexiveFromMorphology,
  secondaryTagsForPos,
  verbFormFromMorphology,
  voiceFromMorphology,
} from "@/app/core/morphology"

import {
  GRAM_POS_LABELS,
  GRAM_FEATURE_LABELS,
  type CorSearchBadge,
  COR_SECONDARY_BADGE_CLASS_BY_LABEL,
  corSecondaryBadgeClass,
  UD_POS_PRIMARY_LABELS,
} from "./cor-constants"

export {
  GRAM_POS_LABELS,
  GRAM_FEATURE_LABELS,
  type CorSearchBadge,
  COR_SECONDARY_BADGE_CLASS_BY_LABEL,
  corSecondaryBadgeClass,
  UD_POS_PRIMARY_LABELS,
}

/**
 * Multi-word expression detection.
 *
 * The backend normalizes MWE pos_tag → standard UD ("VERB" for phrasal verbs and
 * verbal idioms, "NOUN" for nominal idioms, etc.). The phrasal-verb-vs-regular-verb
 * distinction is then carried purely by the lemma being multi-word. Helpers below
 * derive the user-visible "Phrasal verb" / "Idiom" label from that signal.
 */
export function isMultiWordLemma(lemma: string | null | undefined): boolean {
  return typeof lemma === "string" && lemma.trim().includes(" ")
}

/**
 * Returns the MWE-aware primary POS label for a lemma. Multi-word VERB lemmas
 * (phrasal verbs like "se ud", "passe på") render as "Phrasal verb". Multi-word
 * non-VERB lemmas (nominal/adjectival idioms) render as "Idiom". Falls back to
 * `primaryPosLabel(posTag)` for single-word lemmas.
 */
export function primaryPosLabelForLemma(
  posTag: string | null,
  lemma: string | null | undefined,
): string | null {
  if (isMultiWordLemma(lemma)) {
    const upper = (posTag ?? "").toUpperCase().replace(/[\s-]/g, "_")
    // Verbal MWEs render as "Phrasal verb". The backend normalizes
    // phrasal_verb / idiom → UD VERB, but accept the legacy strings too in case
    // older saved rows or tests still carry them.
    if (upper === "VERB" || upper === "AUX" || upper === "PHRASAL_VERB" || upper === "MWE") {
      return "Phrasal verb"
    }
    // Explicit "IDIOM" pos_tag or non-VERB multi-word lemma → "Idiom".
    return "Idiom"
  }
  return primaryPosLabel(posTag)
}

export function primaryPosLabel(posTag: string | null): string | null {
  if (!posTag) {
    return null
  }
  const upper = posTag.toUpperCase()
  return UD_POS_PRIMARY_LABELS[upper] ?? UD_POS_PRIMARY_LABELS[posTag] ?? posTag
}

export function filterAdjectiveBadges(badges: CorSearchBadge[], posTag?: string | null): CorSearchBadge[] {
  const isAdjective = (posTag?.toUpperCase() === "ADJ") || badges.some((b) => b.label === "Adjective" && b.tone === "primary")
  if (!isAdjective) {
    return badges
  }

  const hasSingular = badges.some((b) => b.label === "Singular")
  const hasPlural = badges.some((b) => b.label === "Plural")
  const hasNWord = badges.some((b) => b.label === "n-word")
  const hasTWord = badges.some((b) => b.label === "t-word")
  const hasDefinite = badges.some((b) => b.label === "Definite")
  const hasIndefinite = badges.some((b) => b.label === "Indefinite")

  const excludeLabels = new Set<string>()
  if (hasSingular && hasPlural) {
    excludeLabels.add("Singular")
    excludeLabels.add("Plural")
  }
  if (hasNWord && hasTWord) {
    excludeLabels.add("n-word")
    excludeLabels.add("t-word")
  }
  if (hasDefinite && hasIndefinite) {
    excludeLabels.add("Definite")
    excludeLabels.add("Indefinite")
  }

  if (excludeLabels.size === 0) {
    return badges
  }

  return badges.filter((b) => !excludeLabels.has(b.label))
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

  const uniqueBadges = labels.filter((badge, index, array) => array.findIndex((candidate) => candidate.label === badge.label) === index)
  return filterAdjectiveBadges(uniqueBadges)
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
  const translationParts = normalizedLemmaTranslation
    .split(",")
    .map((part) => normalizedGlossPart(part))
    .filter((part): part is string => Boolean(part))
  if (translationParts.some((part) => part.localeCompare(normalizedGlossTranslation, "en", { sensitivity: "base" }) === 0)) {
    return normalizedLemmaTranslation
  }
  return `${normalizedLemmaTranslation} (${normalizedGlossTranslation})`
}

export function lemmaTranslationWithGlossComma(
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
  const translationParts = normalizedLemmaTranslation
    .split(",")
    .map((part) => normalizedGlossPart(part))
    .filter((part): part is string => Boolean(part))
  if (translationParts.some((part) => part.localeCompare(normalizedGlossTranslation, "en", { sensitivity: "base" }) === 0)) {
    return normalizedLemmaTranslation
  }
  return `${normalizedLemmaTranslation}, ${normalizedGlossTranslation}`
}

export function additionalTranslationsDisplay(
  primaryTranslation: string | null | undefined,
  additionalTranslations: string[] | null | undefined,
): string | null {
  const normalizedPrimary = normalizedGlossPart(primaryTranslation)
  const values: string[] = []
  const seen = new Set<string>()
  if (normalizedPrimary) {
    values.push(normalizedPrimary)
    seen.add(normalizedPrimary.toLocaleLowerCase("en"))
  }
  for (const translation of additionalTranslations ?? []) {
    const normalized = normalizedGlossPart(translation)
    if (!normalized) {
      continue
    }
    const key = normalized.toLocaleLowerCase("en")
    if (seen.has(key)) {
      continue
    }
    seen.add(key)
    values.push(normalized)
  }
  if (values.length === 0) {
    return null
  }
  return values.join(", ")
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
  /** Optional. When provided AND the lemma is multi-word, the primary badge
   * becomes "Phrasal verb" / "Idiom" instead of the bare POS label. */
  lemma?: string | null
}): CorSearchBadge[] {
  const primaryLabel = form.lemma !== undefined
    ? primaryPosLabelForLemma(form.pos_tag ?? null, form.lemma)
    : primaryPosLabel(form.pos_tag ?? null)
  
  let badges: CorSearchBadge[]
  if (form.gram_raw?.trim()) {
    const fromGram = badgesFromGramRaw(form.gram_raw)
    if (!primaryLabel || !isMultiWordLemma(form.lemma)) {
      badges = fromGram
    } else {
      // For MWE lemmas, replace the primary gram-derived badge with the MWE label
      // so the user sees "Phrasal verb" rather than "Verb" for "se ud" / "passe på".
      const withoutPrimary = fromGram.filter((badge) => badge.tone !== "primary")
      badges = [{ label: primaryLabel, tone: "primary" as const }, ...withoutPrimary]
    }
  } else {
    badges = [
      ...(primaryLabel ? [{ label: primaryLabel, tone: "primary" as const }] : []),
      ...savedSecondaryTagsForPos(form.pos_tag ?? null, form.morphology ?? null).map((tag) => ({
        label: tag,
        tone: "secondary" as const,
      })),
    ]
  }

  return filterAdjectiveBadges(badges, form.pos_tag)
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
  const pronType = pronTypeFromMorphology(morphology)
  const person = personFromMorphology(morphology)
  const possession = possessionFromMorphology(morphology)
  const reflexive = reflexiveFromMorphology(morphology)
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
    tags.push(wordType, pronType, possession, number, definiteness)
  }
  if (posTag === "ADJ") {
    tags.push(wordType, number, definiteness, comparableDegree)
  }
  if (posTag === "PRON") {
    tags.push(wordType, pronType, possession, reflexive, person, number, caseLabel)
  }
  if (posTag === "ADV") {
    tags.push(pronType, comparableDegree)
  }

  if (tags.length === 0) {
    return secondaryTagsForPos(posTag, morphology)
  }

  return tags.filter((tag, index, values): tag is string => Boolean(tag) && values.indexOf(tag) === index)
}

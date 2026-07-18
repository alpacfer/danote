import type { WordbankLemma } from "@/app/core"

export type SpecimenTranslationGroup = {
  englishTranslation: string | null
  additionalTranslations: string[]
}

export function wordbankSpecimenTranslationGroups(
  lemma: WordbankLemma,
): SpecimenTranslationGroup[] {
  const sourceGroups = lemma.translation_groups?.length
    ? lemma.translation_groups
    : lemma.english_translation
      ? [{ english_translation: lemma.english_translation, additional_translations: [] }]
      : []
  const seen = new Set<string>()

  return sourceGroups.flatMap((group) => {
    const primary = uniqueTranslation(group.english_translation, seen)
    const additional = (group.additional_translations ?? []).flatMap((translation) => {
      const unique = uniqueTranslation(translation, seen)
      return unique ? [unique] : []
    })
    if (!primary && additional.length === 0) return []
    return [{ englishTranslation: primary, additionalTranslations: additional }]
  })
}

export function wordbankSpecimenDescription(
  posLabels: string[],
  translationGroups: SpecimenTranslationGroup[],
): string {
  const translations = translationGroups.flatMap((group) => [
    ...(group.englishTranslation ? [group.englishTranslation] : []),
    ...group.additionalTranslations,
  ])
  return [...posLabels, ...translations].join(". ")
}

function uniqueTranslation(value: string | null | undefined, seen: Set<string>): string | null {
  const cleaned = value?.trim()
  if (!cleaned) return null
  const normalized = cleaned.toLocaleLowerCase("en")
  if (seen.has(normalized)) return null
  seen.add(normalized)
  return cleaned
}

import {
  normalizeSearchWord,
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
} from "@/app/core"

import type { EnResolveResult, EnTranslatedCorResults } from "@/app/chrome/sidebar/sidebar-search-types"

export function hasExactCorFormMatch(groups: CORSearchGroup[], normalizedQuery: string): boolean {
  return groups.some((group) =>
    (group.variants ?? []).some((variant) => normalizeSearchWord(variant.form) === normalizedQuery),
  )
}

export function detectQueryLanguage(text: string): "da" | "en" | "unknown" {
  if (/[æøåÆØÅ]/u.test(text)) return "da"
  if ([...text].every((char) => char.charCodeAt(0) <= 0x7f)) return "en"
  return "unknown"
}

function matchingCorGroupsForEnglishSource(
  payload: CORSearchFormResponse,
  sourceGroup: ENPosGroup,
  englishQuery: string,
  translationKey: string,
): CORSearchGroup[] {
  const allGroups = payload.groups ?? []
  const withFormMatch = allGroups
    .map((group) => ({
      ...group,
      variants: (group.variants ?? []).filter(
        (variant) => normalizeSearchWord(variant.form) === translationKey,
      ),
    }))
    .filter((group) => group.variants.length > 0)
  const matchingPosGroups = withFormMatch.filter(
    (group) => String(group.pos_tag ?? "").toUpperCase() === sourceGroup.pos_ud.toUpperCase(),
  )
  const groupsToUse = matchingPosGroups.length > 0 ? matchingPosGroups : withFormMatch
  const bestByForm = selectBestCorVariantByForm(groupsToUse, englishQuery)

  return bestByForm.map(({ group, variant }) => ({
    ...group,
    variants: [
      {
        ...variant,
        english_source_description: sourceGroup.meaning_description,
        lemma_translation: englishQuery,
        saveable_translation: englishQuery,
      },
    ],
  }))
}

function selectBestCorVariantByForm(
  groups: CORSearchGroup[],
  englishQuery: string,
): Array<{ group: CORSearchGroup; variant: CORSearchVariant }> {
  const byForm = new Map<string, { group: CORSearchGroup; variant: CORSearchVariant; score: number }>()
  for (const group of groups) {
    for (const variant of group.variants ?? []) {
      const formKey = normalizeSearchWord(variant.form)
      if (!formKey) {
        continue
      }
      const candidate = { group, variant, score: scoreEnglishCorVariant(variant, englishQuery) }
      const current = byForm.get(formKey)
      if (!current || candidate.score > current.score) {
        byForm.set(formKey, candidate)
      }
    }
  }
  return [...byForm.values()].map(({ group, variant }) => ({ group, variant }))
}

function scoreEnglishCorVariant(variant: CORSearchVariant, englishQuery: string): number {
  const queryKey = normalizeSearchWord(englishQuery)
  const saveableKey = normalizeSearchWord(variant.saveable_translation ?? "")
  const lemmaTranslationKey = normalizeSearchWord(variant.lemma_translation ?? "")
  if (saveableKey && saveableKey === queryKey) {
    return 30
  }
  if (lemmaTranslationKey && lemmaTranslationKey === queryKey) {
    return 20
  }
  return 0
}

export function buildEnTranslatedCorResults(
  activeEnResolveResult: EnResolveResult | null,
  payloads: Record<string, CORSearchFormResponse>,
  normalizedQuery: string,
): EnTranslatedCorResults {
  if (!activeEnResolveResult || activeEnResolveResult.query !== normalizedQuery) {
    return {
      orderedCorSearchGroups: [],
      corSearchVariantsToRender: [],
      fallbackEnPosGroups: [],
    }
  }

  const orderedCorSearchGroups: CORSearchGroup[] = []
  const corSearchVariantsToRender: Array<{ group: CORSearchGroup; variant: CORSearchVariant }> = []
  const fallbackEnPosGroups: ENPosGroup[] = []
  const seenVariantCorIds = new Set<string>()
  const renderedTranslationKeys = new Set<string>()

  for (const sourceGroup of activeEnResolveResult.groups) {
    const translationKey = normalizeSearchWord(sourceGroup.danish_translation ?? "")
    if (!translationKey) {
      continue
    }
    const payload = payloads[translationKey]
    if (!payload) {
      if (!renderedTranslationKeys.has(translationKey)) {
        fallbackEnPosGroups.push(sourceGroup)
      }
      continue
    }
    const matchingGroups = matchingCorGroupsForEnglishSource(payload, sourceGroup, normalizedQuery, translationKey)
    let addedAny = false
    for (const group of matchingGroups) {
      const variants = (group.variants ?? []).filter((variant) => {
        if (seenVariantCorIds.has(variant.cor_id)) {
          return false
        }
        seenVariantCorIds.add(variant.cor_id)
        return true
      })
      if (variants.length === 0) {
        continue
      }
      const transformedGroup: CORSearchGroup = { ...group, variants }
      orderedCorSearchGroups.push(transformedGroup)
      for (const variant of variants) {
        corSearchVariantsToRender.push({ group: transformedGroup, variant })
      }
      addedAny = true
    }
    if (addedAny) {
      renderedTranslationKeys.add(translationKey)
    } else if (!renderedTranslationKeys.has(translationKey)) {
      fallbackEnPosGroups.push(sourceGroup)
    }
  }

  return { orderedCorSearchGroups, corSearchVariantsToRender, fallbackEnPosGroups }
}

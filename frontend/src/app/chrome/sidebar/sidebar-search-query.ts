import {
  normalizeSearchWord,
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type ENPosGroup,
  type SavedNote,
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

export function matchingNotesForQuery(savedNotes: SavedNote[], normalizedQuery: string): SavedNote[] {
  if (!normalizedQuery) {
    return []
  }
  return savedNotes
    .filter((note) => {
      const name = note.name.trim().toLocaleLowerCase("da-DK")
      const text = note.text.trim().toLocaleLowerCase("da-DK")
      return name.includes(normalizedQuery) || text.includes(normalizedQuery)
    })
    .slice(0, 8)
}

function matchingCorGroupsForEnglishSource(
  payload: CORSearchFormResponse,
  sourceGroup: ENPosGroup,
  englishQuery: string,
): CORSearchGroup[] {
  const allGroups = payload.groups ?? []
  const matchingPosGroups = allGroups.filter(
    (group) => String(group.pos_tag ?? "").toUpperCase() === sourceGroup.pos_ud.toUpperCase(),
  )
  const groupsToUse = matchingPosGroups.length > 0 ? matchingPosGroups : allGroups

  return groupsToUse.map((group) => ({
    ...group,
    variants: (group.variants ?? []).map((variant) => ({
      ...variant,
      lemma_translation: englishQuery,
      saveable_translation: englishQuery,
    })),
  }))
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
  const seenVariantKeys = new Set<string>()

  for (const sourceGroup of activeEnResolveResult.groups) {
    const translationKey = normalizeSearchWord(sourceGroup.danish_translation ?? "")
    if (!translationKey) {
      continue
    }
    const payload = payloads[translationKey]
    if (!payload) {
      fallbackEnPosGroups.push(sourceGroup)
      continue
    }
    const matchingGroups = matchingCorGroupsForEnglishSource(payload, sourceGroup, normalizedQuery)
    let addedAny = false
    for (const group of matchingGroups) {
      const variants = (group.variants ?? []).filter((variant) => {
        const uniqueKey = `${translationKey}:${sourceGroup.pos_ud}:${variant.cor_id}`
        if (seenVariantKeys.has(uniqueKey)) {
          return false
        }
        seenVariantKeys.add(uniqueKey)
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
    if (!addedAny) {
      fallbackEnPosGroups.push(sourceGroup)
    }
  }

  return { orderedCorSearchGroups, corSearchVariantsToRender, fallbackEnPosGroups }
}

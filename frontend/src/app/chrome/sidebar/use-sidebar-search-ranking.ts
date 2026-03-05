import { useMemo } from "react"

import {
  normalizeSearchWord,
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type WordbankLemma,
} from "@/app/core"

type SearchApiMatch = { lemma: WordbankLemma; matchSurface: string | null }

type CorVariantCandidate = { group: CORSearchGroup; variant: CORSearchVariant }

type UseSidebarSearchRankingParams = {
  lemmas: WordbankLemma[]
  normalizedQuery: string
  searchApiMatches: SearchApiMatch[]
  activeCorFormSearchResult: { query: string; payload: CORSearchFormResponse } | null
}
const scoreWordbankResult = (payload: {
  query: string
  lemmaKey: string
  linkedForm: string
  matchSurface: string
  isExactSaved: boolean
}): number => {
  if (!payload.query) {
    return 0
  }
  if (payload.isExactSaved) {
    return 520
  }
  if (payload.lemmaKey === payload.query) {
    return 480
  }
  if (payload.linkedForm && payload.linkedForm === payload.query) {
    return 400
  }
  if (payload.matchSurface && payload.matchSurface === payload.query) {
    return 360
  }
  if (payload.linkedForm && payload.linkedForm.includes(payload.query)) {
    return 280
  }
  if (payload.matchSurface && payload.matchSurface.includes(payload.query)) {
    return 240
  }
  if (payload.lemmaKey.startsWith(payload.query)) {
    return 200
  }
  return 0
}
const scoreCorGroup = (group: CORSearchGroup, normalizedQuery: string, savedLemmaKeySet: Set<string>): number => {
  let best = 0
  for (const variant of group.variants ?? []) {
    const formKey = normalizeSearchWord(variant.form)
    const lemmaKey = normalizeSearchWord(variant.lemma)
    const isVariationCandidate = formKey !== lemmaKey
    const isVariationAdd = isVariationCandidate && savedLemmaKeySet.has(lemmaKey)
    if (isVariationAdd && formKey === normalizedQuery) {
      best = Math.max(best, 400)
      continue
    }
    if (isVariationAdd) {
      best = Math.max(best, 320)
      continue
    }
    if (formKey === normalizedQuery) {
      best = Math.max(best, 240)
      continue
    }
    if (formKey.startsWith(normalizedQuery)) {
      best = Math.max(best, 160)
    }
  }
  return best
}
export function useSidebarSearchRanking({
  lemmas,
  normalizedQuery,
  searchApiMatches,
  activeCorFormSearchResult,
}: UseSidebarSearchRankingParams) {
  const wordbankResults = useMemo(
    () => searchApiMatches.map((item) => ({ lemma: item.lemma, matchSurface: item.matchSurface ?? null })),
    [searchApiMatches],
  )
  const savedLemmaKeySet = useMemo(
    () => new Set(lemmas.map((item) => normalizeSearchWord(item.lemma)).filter(Boolean)),
    [lemmas],
  )
  const corSearchGroups = useMemo(
    () => activeCorFormSearchResult?.payload.groups ?? [],
    [activeCorFormSearchResult],
  )
  const corSearchVariants = useMemo(
    () => corSearchGroups.flatMap((group) => (group.variants ?? []).map((variant) => ({ group, variant }))),
    [corSearchGroups],
  )
  const addVariationBySavedLemma = useMemo(() => {
    const linked = new Map<string, CorVariantCandidate>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    const savedLemmaKeys = new Set(wordbankResults.map(({ lemma }) => normalizeSearchWord(lemma.lemma)))
    for (const candidate of corSearchVariants) {
      const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
      if (!lemmaKey || !savedLemmaKeys.has(lemmaKey)) {
        continue
      }
      const formKey = normalizeSearchWord(candidate.variant.form)
      if (!formKey || formKey === lemmaKey || formKey !== normalizedQuery) {
        continue
      }
      const existing = linked.get(lemmaKey)
      if (!existing || normalizeSearchWord(existing.variant.form) !== normalizedQuery) {
        linked.set(lemmaKey, candidate)
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])
  const displayVariantBySavedLemma = useMemo(() => {
    const linked = new Map<string, CorVariantCandidate>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    const savedLemmaKeys = new Set(wordbankResults.map(({ lemma }) => normalizeSearchWord(lemma.lemma)))
    for (const candidate of corSearchVariants) {
      const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
      const formKey = normalizeSearchWord(candidate.variant.form)
      if (!lemmaKey || !savedLemmaKeys.has(lemmaKey) || !formKey || formKey !== normalizedQuery) {
        continue
      }
      const existing = linked.get(lemmaKey)
      if (!existing || normalizeSearchWord(existing.variant.form) !== normalizedQuery) {
        linked.set(lemmaKey, candidate)
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])
  const exactSavedVariationLemmaKeySet = useMemo(
    () => new Set(
      wordbankResults
        .filter(({ matchSurface }) => normalizeSearchWord(matchSurface ?? "") === normalizedQuery)
        .map(({ lemma }) => normalizeSearchWord(lemma.lemma))
        .filter(Boolean),
    ),
    [normalizedQuery, wordbankResults],
  )

  const orderedWordbankResults = useMemo(() => {
    return [...wordbankResults].sort((left, right) => {
      const leftLemmaKey = normalizeSearchWord(left.lemma.lemma)
      const rightLemmaKey = normalizeSearchWord(right.lemma.lemma)
      const leftLinked = addVariationBySavedLemma.get(leftLemmaKey)?.variant ?? null
      const rightLinked = addVariationBySavedLemma.get(rightLemmaKey)?.variant ?? null
      const leftScore = scoreWordbankResult({
        query: normalizedQuery,
        lemmaKey: leftLemmaKey,
        linkedForm: normalizeSearchWord(leftLinked?.form ?? ""),
        matchSurface: normalizeSearchWord(left.matchSurface ?? ""),
        isExactSaved: exactSavedVariationLemmaKeySet.has(leftLemmaKey),
      })
      const rightScore = scoreWordbankResult({
        query: normalizedQuery,
        lemmaKey: rightLemmaKey,
        linkedForm: normalizeSearchWord(rightLinked?.form ?? ""),
        matchSurface: normalizeSearchWord(right.matchSurface ?? ""),
        isExactSaved: exactSavedVariationLemmaKeySet.has(rightLemmaKey),
      })
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      return left.lemma.lemma.localeCompare(right.lemma.lemma, "da-DK")
    })
  }, [addVariationBySavedLemma, exactSavedVariationLemmaKeySet, normalizedQuery, wordbankResults])

  const corSearchVariantsToRender = useMemo(
    () => corSearchVariants.filter((candidate) => {
      const formKey = normalizeSearchWord(candidate.variant.form)
      const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
      const isExactSavedVariation = formKey === normalizedQuery && exactSavedVariationLemmaKeySet.has(lemmaKey)
      if (isExactSavedVariation) {
        return false
      }
      const linked = addVariationBySavedLemma.get(lemmaKey)
      return !linked || linked.variant.cor_id !== candidate.variant.cor_id
    }),
    [addVariationBySavedLemma, corSearchVariants, exactSavedVariationLemmaKeySet, normalizedQuery],
  )

  const orderedCorSearchGroups = useMemo(
    () => [...corSearchGroups].sort((left, right) => {
      const leftScore = scoreCorGroup(left, normalizedQuery, savedLemmaKeySet)
      const rightScore = scoreCorGroup(right, normalizedQuery, savedLemmaKeySet)
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      return left.lemma.localeCompare(right.lemma, "da-DK")
    }),
    [corSearchGroups, normalizedQuery, savedLemmaKeySet],
  )

  return {
    savedLemmaKeySet,
    addVariationBySavedLemma,
    displayVariantBySavedLemma,
    exactSavedVariationLemmaKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults: orderedWordbankResults.length > 0 || corSearchVariantsToRender.length > 0,
    hasWordbankActions: corSearchVariantsToRender.length > 0,
  }
}

import { useMemo } from "react"

import {
  normalizeSearchWord,
  type CORSearchFormResponse,
  type CORSearchGroup,
  type CORSearchVariant,
  type WordbankLemma,
  type WordbankSearchItem,
} from "@/app/core"

type CorVariantCandidate = { group: CORSearchGroup; variant: CORSearchVariant }

type UseSidebarSearchRankingParams = {
  lemmas: WordbankLemma[]
  normalizedQuery: string
  searchApiMatches: WordbankSearchItem[]
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

const scoreCorGroup = (
  group: CORSearchGroup,
  normalizedQuery: string,
  variationCandidateCorIdSet: Set<string>,
): number => {
  let best = 0
  for (const variant of group.variants ?? []) {
    const formKey = normalizeSearchWord(variant.form)
    const lemmaKey = normalizeSearchWord(variant.lemma)
    const isVariationAdd = formKey !== lemmaKey && variationCandidateCorIdSet.has(variant.cor_id)
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
    () => searchApiMatches.map((item) => ({ ...item, query_cor_ids: item.query_cor_ids ?? [] })),
    [searchApiMatches],
  )
  const corSearchGroups = useMemo(
    () => activeCorFormSearchResult?.payload.groups ?? [],
    [activeCorFormSearchResult],
  )
  const corSearchVariants = useMemo(
    () => corSearchGroups.flatMap((group) => (group.variants ?? []).map((variant) => ({ group, variant }))),
    [corSearchGroups],
  )
  const variationCandidateCorIdSet = useMemo(
    () =>
      new Set(
        corSearchVariants
          .filter((candidate) => {
            const formKey = normalizeSearchWord(candidate.variant.form)
            const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
            return (
              formKey
              && lemmaKey
              && formKey !== lemmaKey
              && candidateMatchesAnySavedMeaning(candidate, wordbankResults, lemmas)
            )
          })
          .map((candidate) => candidate.variant.cor_id),
      ),
    [corSearchVariants, lemmas, wordbankResults],
  )

  const addVariationBySavedResult = useMemo(() => {
    const linked = new Map<string, CorVariantCandidate>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    for (const savedResult of wordbankResults) {
      const savedKey = savedWordbankResultKey(savedResult)
      const lemmaKey = normalizeSearchWord(savedResult.lemma)
      const savedMatchSurfaceKey = normalizeSearchWord(savedResult.match_surface ?? "")
      if (lemmaKey !== normalizedQuery && savedMatchSurfaceKey !== normalizedQuery) {
        continue
      }
      for (const candidate of corSearchVariants) {
        if (!candidateMatchesSavedResult(candidate, savedResult)) {
          continue
        }
        const formKey = normalizeSearchWord(candidate.variant.form)
        if (!formKey || formKey === lemmaKey || formKey !== normalizedQuery) {
          continue
        }
        linked.set(savedKey, candidate)
        break
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])

  const displayVariantBySavedResult = useMemo(() => {
    const linked = new Map<string, CorVariantCandidate>()
    if (!normalizedQuery || wordbankResults.length === 0 || corSearchVariants.length === 0) {
      return linked
    }

    for (const savedResult of wordbankResults) {
      const savedKey = savedWordbankResultKey(savedResult)
      const lemmaKey = normalizeSearchWord(savedResult.lemma)
      const savedMatchSurfaceKey = normalizeSearchWord(savedResult.match_surface ?? "")
      if (lemmaKey !== normalizedQuery && savedMatchSurfaceKey !== normalizedQuery) {
        continue
      }
      for (const candidate of corSearchVariants) {
        if (!candidateMatchesSavedResult(candidate, savedResult)) {
          continue
        }
        const formKey = normalizeSearchWord(candidate.variant.form)
        if (!formKey || formKey !== normalizedQuery) {
          continue
        }
        linked.set(savedKey, candidate)
        break
      }
    }
    return linked
  }, [corSearchVariants, normalizedQuery, wordbankResults])

  const exactSavedVariationKeySet = useMemo(
    () =>
      new Set(
        wordbankResults
          .filter((item) => {
            const lemmaKey = normalizeSearchWord(item.lemma)
            const matchSurfaceKey = normalizeSearchWord(item.match_surface ?? "")
            return lemmaKey === normalizedQuery || matchSurfaceKey === normalizedQuery
          })
          .map(savedWordbankResultKey),
      ),
    [normalizedQuery, wordbankResults],
  )

  const savedQueryCorIdSet = useMemo(
    () =>
      new Set(
        wordbankResults
          .flatMap((item) => item.query_cor_ids ?? [])
          .map((item) => item.trim())
          .filter(Boolean),
      ),
    [wordbankResults],
  )

  const addVariationCorIdSet = useMemo(
    () => new Set([...addVariationBySavedResult.values()].map((candidate) => candidate.variant.cor_id)),
    [addVariationBySavedResult],
  )

  // Variants whose form equals the saved lemma (query == lemma) are the saved
  // word itself, not a new addable variation. They must be filtered from the
  // CoR "add" cards even when the saved row carries no query_cor_ids — e.g.
  // static presaved words, pronouns, hv-words, and builtins all return an
  // empty query_cor_ids list, so the savedQueryCorIdSet check alone leaks
  // them through as duplicates.
  const displaySavedCorIdSet = useMemo(
    () => new Set([...displayVariantBySavedResult.values()].map((candidate) => candidate.variant.cor_id)),
    [displayVariantBySavedResult],
  )

  const orderedWordbankResults = useMemo(() => {
    return [...wordbankResults].sort((left, right) => {
      const leftKey = savedWordbankResultKey(left)
      const rightKey = savedWordbankResultKey(right)
      const leftLemmaKey = normalizeSearchWord(left.lemma)
      const rightLemmaKey = normalizeSearchWord(right.lemma)
      const leftLinked = addVariationBySavedResult.get(leftKey)?.variant ?? null
      const rightLinked = addVariationBySavedResult.get(rightKey)?.variant ?? null
      const leftScore = scoreWordbankResult({
        query: normalizedQuery,
        lemmaKey: leftLemmaKey,
        linkedForm: normalizeSearchWord(leftLinked?.form ?? ""),
        matchSurface: normalizeSearchWord(left.match_surface ?? ""),
        isExactSaved: exactSavedVariationKeySet.has(leftKey),
      })
      const rightScore = scoreWordbankResult({
        query: normalizedQuery,
        lemmaKey: rightLemmaKey,
        linkedForm: normalizeSearchWord(rightLinked?.form ?? ""),
        matchSurface: normalizeSearchWord(right.match_surface ?? ""),
        isExactSaved: exactSavedVariationKeySet.has(rightKey),
      })
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      if (left.lemma !== right.lemma) {
        return left.lemma.localeCompare(right.lemma, "da-DK")
      }
      return (left.meaning_id ?? 0) - (right.meaning_id ?? 0)
    })
  }, [addVariationBySavedResult, exactSavedVariationKeySet, normalizedQuery, wordbankResults])

  const corSearchVariantsToRender = useMemo(
    () =>
      corSearchVariants.filter((candidate) => {
        // Sense-fan-out variants carry their own meaning_key + saved_meaning_id,
        // so each per-sense card decides for itself whether to render as
        // "saved (eye)" or "add (plus)". The legacy cor_id-based filters below
        // assumed one variant per lemma and would otherwise drop EVERY
        // discovered sense the moment any one sense was saved (because every
        // variant of the same lemma shares the same cor_id) — that's exactly
        // the regression where post-save search hides the still-unsaved senses.
        if (candidate.variant.meaning_key) {
          return true
        }
        if (savedQueryCorIdSet.has(candidate.variant.cor_id)) {
          return false
        }
        if (addVariationCorIdSet.has(candidate.variant.cor_id)) {
          return false
        }
        if (displaySavedCorIdSet.has(candidate.variant.cor_id)) {
          return false
        }
        return true
      }),
    [addVariationCorIdSet, corSearchVariants, displaySavedCorIdSet, savedQueryCorIdSet],
  )

  const orderedCorSearchGroups = useMemo(
    () => [...corSearchGroups].sort((left, right) => {
      const leftScore = scoreCorGroup(left, normalizedQuery, variationCandidateCorIdSet)
      const rightScore = scoreCorGroup(right, normalizedQuery, variationCandidateCorIdSet)
      if (leftScore !== rightScore) {
        return rightScore - leftScore
      }
      return left.lemma.localeCompare(right.lemma, "da-DK")
    }),
    [corSearchGroups, normalizedQuery, variationCandidateCorIdSet],
  )

  return {
    variationCandidateCorIdSet,
    addVariationBySavedResult,
    displayVariantBySavedResult,
    exactSavedVariationKeySet,
    orderedWordbankResults,
    corSearchVariantsToRender,
    orderedCorSearchGroups,
    hasWordbankSectionResults: orderedWordbankResults.length > 0 || corSearchVariantsToRender.length > 0,
    hasWordbankActions: corSearchVariantsToRender.length > 0,
  }
}

function savedWordbankResultKey(item: WordbankSearchItem): string {
  const lemmaKey = normalizeSearchWord(item.lemma)
  return `${lemmaKey}::${item.meaning_id ?? "root"}::${item.cor_lemma_idx ?? "none"}`
}

function candidateMatchesSavedResult(
  candidate: CorVariantCandidate,
  savedResult: WordbankSearchItem,
): boolean {
  if (
    savedResult.cor_lemma_idx !== null
    && savedResult.cor_lemma_idx !== undefined
  ) {
    return savedResult.cor_lemma_idx === candidate.variant.lemma_idx
  }
  return savedResult.meaning_id == null
    && normalizeSearchWord(savedResult.lemma) === normalizeSearchWord(candidate.variant.lemma)
}

function candidateMatchesAnySavedMeaning(
  candidate: CorVariantCandidate,
  savedResults: WordbankSearchItem[],
  lemmas: WordbankLemma[],
): boolean {
  for (const savedResult of savedResults) {
    if (candidateMatchesSavedResult(candidate, savedResult)) {
      return true
    }
  }

  const lemmaKey = normalizeSearchWord(candidate.variant.lemma)
  if (!lemmaKey) {
    return false
  }

  const candidateMeaningKeySet = new Set(
    [candidate.group.gloss, candidate.variant.gloss, candidate.variant.lemma_translation]
      .map((value) => normalizeSearchWord(value ?? ""))
      .filter(Boolean),
  )
  if (candidateMeaningKeySet.size === 0) {
    return false
  }

  return lemmas.some((lemma) => {
    if (normalizeSearchWord(lemma.lemma) !== lemmaKey) {
      return false
    }
    const translationKey = normalizeSearchWord(lemma.english_translation ?? "")
    return Boolean(translationKey) && candidateMeaningKeySet.has(translationKey)
  })
}

export { savedWordbankResultKey }

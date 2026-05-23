import type { CorSearchBadge } from "@/app/core"
import { getQuestionWordEntry } from "@/app/sections/wordbank/question-words/question-words-data"

const HV_PINNED_SENTINEL = "__pinned_hv_questions"
const PRONOUNS_PINNED_SENTINEL = "__pinned_pronouns"
const PREPOSITIONS_PINNED_SENTINEL = "__pinned_prepositions"
const CONJUNCTIONS_PINNED_SENTINEL = "__pinned_conjunctions"

export type PrimaryPosBadgeOverride = {
  label: string
  pinnedSentinel: string
}

/**
 * For pronouns, HV question words, prepositions, and conjunctions, the primary
 * POS badge should:
 *   - render a custom label (HV question words show "HV Word" instead of
 *     their underlying PRON/DET/ADV label)
 *   - on click, navigate to the matching pinned reference page instead of
 *     filtering the wordbank list.
 *
 * Returns null for every other POS — those keep the default label + filter
 * behavior.
 */
export function primaryPosBadgeOverride({
  posTag,
  morphology,
  lemma,
}: {
  posTag: string | null
  morphology: string | null
  lemma: string | null | undefined
}): PrimaryPosBadgeOverride | null {
  const upper = (posTag ?? "").toUpperCase()
  const isInterrogative = (morphology ?? "").includes("PronType=Int")
  if (lemma && isInterrogative && getQuestionWordEntry(lemma)) {
    return { label: "HV Word", pinnedSentinel: HV_PINNED_SENTINEL }
  }
  if (upper === "PRON") {
    return { label: "Pronoun", pinnedSentinel: PRONOUNS_PINNED_SENTINEL }
  }
  if (upper === "ADP") {
    return { label: "Preposition", pinnedSentinel: PREPOSITIONS_PINNED_SENTINEL }
  }
  if (upper === "CCONJ") {
    return { label: "Conjunction", pinnedSentinel: CONJUNCTIONS_PINNED_SENTINEL }
  }
  if (upper === "SCONJ") {
    return { label: "Subordinating conjunction", pinnedSentinel: CONJUNCTIONS_PINNED_SENTINEL }
  }
  return null
}

/**
 * Returns a new badge list with the primary POS badge label replaced by the
 * override label (e.g. interrogative pronouns → "HV Word"). If no override
 * applies, the input badge list is returned unchanged.
 */
export function applyPrimaryBadgeLabelOverride(
  badges: CorSearchBadge[],
  context: { posTag: string | null; morphology: string | null; lemma: string | null | undefined },
): CorSearchBadge[] {
  const override = primaryPosBadgeOverride(context)
  if (!override) return badges
  let replaced = false
  return badges.map((badge) => {
    if (!replaced && badge.tone === "primary") {
      replaced = true
      return { label: override.label, tone: "primary" as const }
    }
    return badge
  })
}

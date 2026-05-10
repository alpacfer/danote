import { badgesForSavedForm, type CorSearchBadge } from "@/app/core"

const SUMMARY_SECONDARY_BADGES_BY_POS: Record<string, Set<string>> = {
  NOUN: new Set(["n-word", "t-word"]),
  DET: new Set(["n-word", "t-word", "Interrogative", "Possessive", "Singular", "Plural"]),
  PRON: new Set([
    "n-word",
    "t-word",
    "Personal",
    "Demonstrative",
    "Interrogative",
    "Relative",
    "Indefinite",
    "Negative",
    "Total",
    "Reciprocal",
    "Possessive",
    "Reflexive",
    "1st person",
    "2nd person",
    "3rd person",
    "Singular",
    "Plural",
  ]),
  ADV: new Set(["Interrogative", "Comparative", "Superlative"]),
}

export function wordPageBadgesForSavedForm(form: {
  pos_tag?: string | null
  morphology?: string | null
  gram_raw?: string | null
}): CorSearchBadge[] {
  const posTag = form.pos_tag?.toUpperCase() ?? null
  const badges = badgesForSavedForm(form)
  const allowedSecondaryBadges = posTag ? SUMMARY_SECONDARY_BADGES_BY_POS[posTag] : undefined

  return badges.filter((badge) => badge.tone === "primary" || allowedSecondaryBadges?.has(badge.label))
}

import {
  formatSavedNoteTimestamp,
  type VerificationAction,
  type VerificationOverview,
  type VerificationTargetView,
} from "@/app/core"

export type WordbankVerificationViewState = "idle" | "queued" | "verified" | "review"

export function getVerificationViewState(overview: VerificationOverview): WordbankVerificationViewState {
  if (overview.reviewCount > 0) {
    return "review"
  }
  if (overview.queuedCount > 0) {
    return "queued"
  }
  if (overview.targets.length > 0 && overview.verifiedCount === overview.targets.length) {
    return "verified"
  }
  return "idle"
}

export function verificationTriggerLabel(state: WordbankVerificationViewState): string {
  if (state === "queued") {
    return "Show verification details (word verification is running)"
  }
  if (state === "review") {
    return "Show verification review details"
  }
  return "Show verification details"
}

export function verificationBadgeLabel(state: WordbankVerificationViewState): string {
  if (state === "queued") {
    return "In progress"
  }
  if (state === "verified") {
    return "Verified"
  }
  if (state === "review") {
    return "Review needed"
  }
  return "Not verified"
}

export function verificationBadgeVariant(
  state: WordbankVerificationViewState,
): "default" | "secondary" | "outline" {
  if (state === "verified") {
    return "default"
  }
  if (state === "queued" || state === "review") {
    return "secondary"
  }
  return "outline"
}

export function verificationHeadline(state: WordbankVerificationViewState): string {
  if (state === "queued") {
    return "Gemini is verifying this word page"
  }
  if (state === "verified") {
    return "Verification completed"
  }
  if (state === "review") {
    return "Verification needs review"
  }
  return "No verification records yet"
}

export function verificationSummary(
  _overview: VerificationOverview,
  state: WordbankVerificationViewState,
): string {
  if (state === "queued") {
    return "Gemini is still processing one or more targets. Results and suggested fixes will appear here as they finish."
  }
  if (state === "verified") {
    return "Gemini verified every visible target on this word page."
  }
  if (state === "review") {
    return "One or more targets need review. Apply the suggested changes from the cards below."
  }
  return "Verification details, progress, and suggested changes will appear here after Gemini processes this word page."
}

export function verificationProgressLabel(
  overview: VerificationOverview,
  state: WordbankVerificationViewState,
): string {
  if (state === "queued") {
    return `${overview.queuedCount} running`
  }
  if (state === "verified") {
    return `${overview.verifiedCount} verified`
  }
  if (state === "review") {
    return `${overview.reviewCount} need review`
  }
  return "Waiting to run"
}

export function verificationCountsSummary(overview: VerificationOverview): string {
  const parts: string[] = []
  if (overview.queuedCount > 0) {
    parts.push(`${overview.queuedCount} queued`)
  }
  if (overview.verifiedCount > 0) {
    parts.push(`${overview.verifiedCount} verified`)
  }
  if (overview.reviewCount > 0) {
    parts.push(`${overview.reviewCount} review`)
  }
  return parts.join(" · ") || "No completed targets"
}

export function groupVerificationTargets(overview: VerificationOverview): {
  reviewTargets: VerificationTargetView[]
  queuedTargets: VerificationTargetView[]
  verifiedTargets: VerificationTargetView[]
  idleTargets: VerificationTargetView[]
} {
  const reviewTargets: VerificationTargetView[] = []
  const queuedTargets: VerificationTargetView[] = []
  const verifiedTargets: VerificationTargetView[] = []
  const idleTargets: VerificationTargetView[] = []

  for (const target of overview.targets) {
    const state = verificationTargetState(target)
    if (state === "review") {
      reviewTargets.push(target)
      continue
    }
    if (state === "queued") {
      queuedTargets.push(target)
      continue
    }
    if (state === "verified") {
      verifiedTargets.push(target)
      continue
    }
    idleTargets.push(target)
  }

  return {
    reviewTargets,
    queuedTargets,
    verifiedTargets,
    idleTargets,
  }
}

export function verificationTargetState(target: VerificationTargetView): WordbankVerificationViewState {
  if (target.errorDetail) {
    return "review"
  }
  if (target.queuedDetail) {
    return "queued"
  }
  if (target.successDetail) {
    return "verified"
  }
  return "idle"
}

export function verificationTargetTimestampMeta(target: VerificationTargetView): { label: string; value: string } {
  if (target.queuedDetail) {
    return {
      label: "Requested",
      value: formatSavedNoteTimestamp(target.queuedDetail.requestedAt),
    }
  }
  if (target.successDetail) {
    return {
      label: "Verified",
      value: formatSavedNoteTimestamp(target.successDetail.verifiedAt),
    }
  }
  if (target.errorDetail) {
    const timestamp = target.verification?.completed_at || target.verification?.requested_at || new Date().toISOString()
    return {
      label: "Reviewed",
      value: formatSavedNoteTimestamp(timestamp),
    }
  }
  return {
    label: "Updated",
    value: "Not verified yet",
  }
}

export function verificationTargetSummary(target: VerificationTargetView): string {
  if (target.queuedDetail) {
    return "Gemini is still processing this target."
  }
  if (target.successDetail) {
    return target.successDetail.rawMessage || "Verification passed."
  }
  if (target.errorDetail) {
    return target.errorDetail.rawMessage || target.errorDetail.problem
  }
  return "Waiting for verification."
}

export function verificationReviewPrimaryCopy(target: VerificationTargetView): string {
  if (target.errorDetail?.problem?.trim()) {
    return target.errorDetail.problem.trim()
  }
  return verificationTargetSummary(target)
}

export function verificationReviewSupportingCopy(target: VerificationTargetView): string | null {
  if (target.errorDetail?.changeToImplement?.trim()) {
    return target.errorDetail.changeToImplement.trim()
  }
  return null
}

export function verificationActionButtonLabel(action: VerificationAction): string {
  return verificationActionTitle(action)
}

export function latestVerifiedTimestamp(targets: VerificationTargetView[]): string | null {
  const verifiedAt = targets
    .map((target) => target.successDetail?.verifiedAt ?? null)
    .filter((value): value is string => Boolean(value))
    .sort((a, b) => b.localeCompare(a))[0] ?? null

  return verifiedAt ? formatSavedNoteTimestamp(verifiedAt) : null
}

export function verificationActionTitle(action: VerificationAction) {
  if (action.action_type === "fix_translation") {
    return "Fix translation"
  }
  if (action.action_type === "fix_variations") {
    return "Fix variations"
  }
  if (action.action_type === "move_to_meaning_section") {
    return "Move to different meaning"
  }
  if (action.action_type === "move_to_lemma") {
    return "Move to different lemma"
  }
  return "Review action"
}

export function verificationActionSummary(action: VerificationAction) {
  if (action.action_type === "fix_translation") {
    return `Set translation to '${action.english_translation ?? ""}'.`
  }
  if (action.action_type === "fix_variations") {
    const slotSummary = formatFixVariationsSlotSummary(action)
    if (slotSummary) {
      return slotSummary
    }
    if (hasAdjectiveFixVariationFields(action)) {
      return "Replace the saved variation set with the reviewed adjective forms for this meaning."
    }
    if (hasVerbFixVariationFields(action)) {
      return "Replace the saved variation set with the reviewed verb forms for this meaning."
    }
    return "Replace the saved variation set with the reviewed noun forms for this meaning."
  }
  if (action.action_type === "move_to_meaning_section") {
    return `Move this entry to meaning section #${action.target_meaning_id ?? "?"}.`
  }
  if (action.action_type === "move_to_lemma") {
    const targetLemma = action.target_lemma ?? "new lemma"
    const targetMeaning = action.target_meaning_key ?? "new meaning"
    return `Move this entry to '${targetLemma}' under '${targetMeaning}'.`
  }
  return "Review the Gemini recommendation."
}

function formatFixVariationsSlotSummary(action: VerificationAction): string | null {
  const summaries = [
    buildFixVariationsSlotLine("Singular indefinite", action.singular_indefinite_forms),
    buildFixVariationsSlotLine("Singular indefinite n-word", action.singular_indefinite_n_word_forms),
    buildFixVariationsSlotLine("Singular indefinite t-word", action.singular_indefinite_t_word_forms),
    buildFixVariationsSlotLine("Singular definite", action.singular_definite_forms),
    buildFixVariationsSlotLine("Plural indefinite", action.plural_indefinite_forms),
    buildFixVariationsSlotLine("Plural definite", action.plural_definite_forms),
    buildFixVariationsSlotLine("Infinitive", action.infinitive_forms),
    buildFixVariationsSlotLine("Present", action.present_forms),
    buildFixVariationsSlotLine("Past", action.past_forms),
    buildFixVariationsSlotLine("Imperative", action.imperative_forms),
    buildFixVariationsSlotLine("Past participle", action.past_participle_forms),
  ].filter(Boolean)
  return summaries.join(" ") || null
}

function hasAdjectiveFixVariationFields(action: VerificationAction): boolean {
  return Boolean(
    (action.singular_indefinite_n_word_forms && action.singular_indefinite_n_word_forms.length > 0)
    || (action.singular_indefinite_t_word_forms && action.singular_indefinite_t_word_forms.length > 0),
  )
}

function hasVerbFixVariationFields(action: VerificationAction): boolean {
  return Boolean(
    (action.infinitive_forms && action.infinitive_forms.length > 0)
    || (action.present_forms && action.present_forms.length > 0)
    || (action.past_forms && action.past_forms.length > 0)
    || (action.imperative_forms && action.imperative_forms.length > 0)
    || (action.past_participle_forms && action.past_participle_forms.length > 0),
  )
}

function buildFixVariationsSlotLine(label: string, forms: string[] | null | undefined): string | null {
  if (!forms || forms.length === 0) {
    return null
  }
  return `${label}: ${forms.join(", ")}.`
}

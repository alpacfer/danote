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

export function verificationActionTitle(action: VerificationAction) {
  if (action.action_type === "fix_translation") {
    return "Fix translation"
  }
  if (action.action_type === "fix_gloss") {
    return "Fix gloss"
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
  if (action.action_type === "fix_gloss") {
    return `Set gloss to '${action.gloss ?? ""}'.`
  }
  if (action.action_type === "fix_variations") {
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

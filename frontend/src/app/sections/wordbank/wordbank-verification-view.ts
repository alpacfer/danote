import type { VerificationErrorDetail, VerificationQueuedDetail, VerificationSuccessDetail } from "@/app/core"
import { formatSavedNoteTimestamp } from "@/app/core"

export type WordbankVerificationViewState = "idle" | "queued" | "verified" | "review"

export function getVerificationViewState(args: {
  selectedLemmaVerificationError: VerificationErrorDetail | null
  selectedLemmaVerificationQueued: VerificationQueuedDetail | null
  selectedLemmaVerificationSuccess: VerificationSuccessDetail | null
}): WordbankVerificationViewState {
  if (args.selectedLemmaVerificationQueued) {
    return "queued"
  }
  if (args.selectedLemmaVerificationSuccess) {
    return "verified"
  }
  if (args.selectedLemmaVerificationError) {
    return "review"
  }
  return "idle"
}

export function getVerificationTimestampMeta(args: {
  selectedLemmaVerificationError: VerificationErrorDetail | null
  selectedLemmaVerificationQueued: VerificationQueuedDetail | null
  selectedLemmaVerificationSuccess: VerificationSuccessDetail | null
  selectedVerificationTimestamp: string
}): { label: string; value: string } {
  if (args.selectedLemmaVerificationQueued) {
    return {
      label: "Requested",
      value: formatSavedNoteTimestamp(args.selectedLemmaVerificationQueued.requestedAt),
    }
  }
  if (args.selectedLemmaVerificationSuccess) {
    return {
      label: "Verified",
      value: formatSavedNoteTimestamp(args.selectedLemmaVerificationSuccess.verifiedAt),
    }
  }
  if (args.selectedLemmaVerificationError) {
    return {
      label: "Reviewed",
      value: formatSavedNoteTimestamp(args.selectedVerificationTimestamp),
    }
  }
  return {
    label: "Updated",
    value: "Not verified yet",
  }
}

export function verificationTriggerLabel(state: WordbankVerificationViewState): string {
  if (state === "queued") {
    return "Show verification details (verification is running)"
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
    return "Gemini is verifying this word"
  }
  if (state === "verified") {
    return "Verification completed"
  }
  if (state === "review") {
    return "Verification needs review"
  }
  return "No verification record yet"
}

export function verificationSummary(args: {
  viewState: WordbankVerificationViewState
  selectedLemmaVerificationError: VerificationErrorDetail | null
  selectedLemmaVerificationQueued: VerificationQueuedDetail | null
  selectedLemmaVerificationSuccess: VerificationSuccessDetail | null
}): string {
  if (args.viewState === "queued") {
    return "Gemini is still processing this entry. The latest status and any suggested fixes will appear here."
  }
  if (args.viewState === "verified") {
    return args.selectedLemmaVerificationSuccess?.rawMessage || "Gemini verified this entry successfully."
  }
  if (args.viewState === "review") {
    return args.selectedLemmaVerificationError?.rawMessage || args.selectedLemmaVerificationError?.problem || "Gemini found an issue that needs review."
  }
  return "Verification details, progress, and suggested changes will appear here after Gemini processes this entry."
}

export function verificationProgressLabel(state: WordbankVerificationViewState): string {
  if (state === "queued") {
    return "Verification in progress"
  }
  if (state === "verified") {
    return "Verification complete"
  }
  if (state === "review") {
    return "Review needed"
  }
  return "Waiting to run"
}

export function verificationActionTitle(action: VerificationErrorDetail["suggestedActions"][number]): string {
  if (action.action_type === "fix_translation") {
    return "Fix translation"
  }
  if (action.action_type === "fix_gloss") {
    return "Fix gloss"
  }
  if (action.action_type === "move_to_meaning_section") {
    return "Move to different meaning"
  }
  if (action.action_type === "move_to_lemma") {
    return "Move to different lemma"
  }
  return "Review action"
}

export function verificationActionSummary(action: VerificationErrorDetail["suggestedActions"][number]): string {
  if (action.action_type === "fix_translation") {
    return `Set translation to '${action.english_translation ?? ""}'.`
  }
  if (action.action_type === "fix_gloss") {
    return `Set gloss to '${action.gloss ?? ""}'.`
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

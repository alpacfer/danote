import { normalizeSearchWord, type AppSection, type LemmaDetailsResponse } from "@/app/core"

export type UseLexiconDataParams = {
  backendUrl: string
  extractErrorMessage: (response: Response, fallback: string) => Promise<string>
  activeSection: AppSection
  selectedLemma: string | null
  selectedMeaningId: number | null
  wordbankRefreshTick: number
  sentencebankRefreshTick: number
}

export type PendingPronunciationFormsByLemma = Record<string, { forms: string[]; expiresAt: number }>

export function hasQueuedRelatedWords(lemmaDetails: LemmaDetailsResponse | null): boolean {
  return lemmaDetails?.related_words?.status === "queued"
}

export function shouldPollPronunciations(args: {
  lemmaDetails: LemmaDetailsResponse | null
  normalizedSelectedLemma: string
  pendingPronunciationFormsByLemma: PendingPronunciationFormsByLemma
}): boolean {
  const details = args.lemmaDetails
  const activeTracking = args.normalizedSelectedLemma
    ? args.pendingPronunciationFormsByLemma[args.normalizedSelectedLemma]
    : undefined
  return Boolean(
    activeTracking
    && activeTracking.expiresAt > Date.now()
    && (
      details === null
      || activeTracking.forms.some((form) => !lemmaDetailsHasPronunciation(details, form))
    ),
  )
}

export function mergeQueuedPronunciationTracking(
  current: PendingPronunciationFormsByLemma,
  lemma: string,
  forms: string[],
  expiresAt: number,
): PendingPronunciationFormsByLemma {
  const existing = current[lemma]
  return {
    ...current,
    [lemma]: {
      forms: normalizeQueuedPronunciationForms([
        ...(existing?.forms ?? []),
        ...forms,
      ]),
      expiresAt,
    },
  }
}

export function normalizeQueuedPronunciationForms(forms: string[]): string[] {
  const ordered: string[] = []
  const seen = new Set<string>()
  for (const form of forms) {
    const normalizedForm = normalizeSearchWord(form)
    if (!normalizedForm || seen.has(normalizedForm)) {
      continue
    }
    seen.add(normalizedForm)
    ordered.push(normalizedForm)
  }
  return ordered
}

export function lemmaDetailsHasPronunciation(lemmaDetails: LemmaDetailsResponse, form: string): boolean {
  const normalizedTarget = normalizeSearchWord(form)
  if (!normalizedTarget) {
    return false
  }
  const candidates = [
    ...(lemmaDetails.surface_forms ?? []),
    ...((lemmaDetails.meaning_sections ?? []).flatMap((section) => section.surface_forms ?? [])),
  ]
  return candidates.some((candidate) => {
    const normalizedForm = normalizeSearchWord(candidate.form)
    return normalizedForm === normalizedTarget && Boolean(candidate.has_pronunciation)
  })
}

import { normalizeSearchWord } from "@/app/core"

type PronunciationCandidate = {
  form: string
  has_pronunciation?: boolean | null
}

export function buildPronunciationAvailabilityMap(
  forms: PronunciationCandidate[],
): Map<string, boolean> {
  const availability = new Map<string, boolean>()
  for (const form of forms) {
    const normalizedForm = normalizeSearchWord(form.form)
    if (!normalizedForm) {
      continue
    }
    if (form.has_pronunciation) {
      availability.set(normalizedForm, true)
    } else if (!availability.has(normalizedForm)) {
      availability.set(normalizedForm, false)
    }
  }
  return availability
}

export function resolvePronunciationAvailability<T extends PronunciationCandidate>(
  forms: T[],
  availability: Map<string, boolean>,
): T[] {
  return forms.map((form) => {
    const normalizedForm = normalizeSearchWord(form.form)
    return {
      ...form,
      has_pronunciation: normalizedForm ? Boolean(availability.get(normalizedForm)) : Boolean(form.has_pronunciation),
    }
  })
}

export function hasPronunciationForForm(
  availability: Map<string, boolean>,
  form: string,
): boolean {
  const normalizedForm = normalizeSearchWord(form)
  return normalizedForm ? Boolean(availability.get(normalizedForm)) : false
}

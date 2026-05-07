import type { SentenceTokenCard } from "@/app/core"
import { getHvQuestionEntry } from "@/app/sections/wordbank/hv-questions/hv-question-data"
import { getPronounCategory, pronounTranslation } from "@/app/sections/wordbank/pronouns/pronouns-data"

function builtinLemmaCandidate(token: SentenceTokenCard): string {
  const candidate = token.lemma_candidate?.trim() ?? ""
  if (candidate) return candidate.toLowerCase()
  return token.surface_form.trim().toLowerCase()
}

export function enrichSentenceTokenWithBuiltins(token: SentenceTokenCard): SentenceTokenCard {
  if (token.save_status === "saved" && typeof token.stored_lemma === "string" && token.stored_lemma.length > 0) {
    return token
  }

  const lemma = builtinLemmaCandidate(token)
  if (!lemma) return token

  const hv = getHvQuestionEntry(lemma)
  if (hv) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: hv.lemma,
      pos_tag: token.pos_tag ?? hv.posTag,
      morphology: token.morphology ?? hv.morphology,
      english_translation: token.english_translation ?? hv.translation,
    }
  }

  if (getPronounCategory(lemma)) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: lemma,
      pos_tag: token.pos_tag ?? "PRON",
      english_translation: token.english_translation ?? pronounTranslation(lemma),
    }
  }

  return token
}

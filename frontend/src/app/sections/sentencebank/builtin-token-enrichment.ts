import type { SentenceTokenCard } from "@/app/core"
import { CONJUNCTION_LEMMAS } from "@/app/sections/wordbank/conjunctions/conjunctions-data"
import { CALENDAR_LEMMAS } from "@/app/sections/wordbank/days-months-seasons/days-months-seasons-data"
import { PREPOSITION_LEMMAS } from "@/app/sections/wordbank/prepositions/prepositions-data"
import { getPronounCategory, pronounTranslation } from "@/app/sections/wordbank/pronouns/pronouns-data"
import { getQuestionWordEntry } from "@/app/sections/wordbank/question-words/question-words-data"

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

  const questionWord = getQuestionWordEntry(lemma)
  if (questionWord) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: questionWord.lemma,
      pos_tag: token.pos_tag ?? questionWord.posTag,
      morphology: token.morphology ?? questionWord.morphology,
      english_translation: token.english_translation ?? questionWord.translation,
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

  if (PREPOSITION_LEMMAS.has(lemma)) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: lemma,
      pos_tag: token.pos_tag ?? "ADP",
    }
  }

  if (CONJUNCTION_LEMMAS.has(lemma)) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: lemma,
      pos_tag: token.pos_tag ?? "CCONJ",
    }
  }

  if (CALENDAR_LEMMAS.has(lemma)) {
    return {
      ...token,
      save_status: "saved",
      stored_lemma: lemma,
      pos_tag: token.pos_tag ?? "NOUN",
    }
  }

  return token
}

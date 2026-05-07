import { normalizeSearchWord, type SentencebankSentence } from "@/app/core"

export function relatedSentencesFor(lemma: string, sentences: SentencebankSentence[]): SentencebankSentence[] {
  return sentences.filter((sentence) => matchedTokenIndexes(lemma, sentence).length > 0)
}

export function matchedTokenIndexes(lemma: string, sentence: SentencebankSentence): number[] {
  const normalizedLemma = normalizeSearchWord(lemma)
  return (sentence.tokens ?? [])
    .filter((token) => (
      normalizeSearchWord(token.stored_lemma ?? token.lemma_candidate ?? "") === normalizedLemma
      || normalizeSearchWord(token.surface_form) === normalizedLemma
    ))
    .map((token) => token.token_index)
}

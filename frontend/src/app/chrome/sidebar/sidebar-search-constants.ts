export const ENGLISH_SEARCH_PHRASES = [
  "Search English words...",
  "Search English sentences...",
  "Search English phrasal verbs...",
]

export const DANISH_SEARCH_PHRASES = [
  "Search Danish words...",
  "Search Danish sentences...",
  "Search Danish phrasal verbs...",
]

export function shuffleArray<T>(array: T[]): T[] {
  const shuffled = [...array]
  for (let i = shuffled.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
  }
  return shuffled
}

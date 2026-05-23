export const CONJUNCTIONS_SENTINEL = "__conjunctions"

export type ConjunctionEntry = {
  lemma: string
  translation: string
  note?: string
}

export const COORDINATING_CONJUNCTION_ROWS: ConjunctionEntry[] = [
  { lemma: "og", translation: "and", note: "Joins clauses or items of equal weight." },
  { lemma: "eller", translation: "or", note: "Alternative." },
  { lemma: "men", translation: "but", note: "Contrast." },
  { lemma: "for", translation: "because / for", note: "Reason; less common than 'fordi'." },
  { lemma: "så", translation: "so", note: "Result or consequence." },
]

export const SUBORDINATING_CONJUNCTION_ROWS: ConjunctionEntry[] = [
  { lemma: "at", translation: "that", note: "Introduces complement clauses: 'jeg ved, at…'." },
  { lemma: "hvis", translation: "if", note: "Conditional. Triggers subordinate word order." },
  { lemma: "fordi", translation: "because", note: "Reason; the most common 'because' word." },
  { lemma: "når", translation: "when (general / future)", note: "Repeated or future events: 'når jeg kommer hjem…'." },
  { lemma: "da", translation: "when (past once) / since", note: "Single past event, or causal 'since'." },
  { lemma: "mens", translation: "while", note: "Two events happening at once." },
  { lemma: "selvom", translation: "although / even though", note: "Concession." },
  { lemma: "inden", translation: "before", note: "Time before another event." },
  { lemma: "før", translation: "before", note: "Synonym of 'inden'." },
  { lemma: "end", translation: "than", note: "Comparison: 'større end mig' = bigger than me." },
  { lemma: "skønt", translation: "although / even though", note: "Concession; literary synonym of 'selvom'." },
  { lemma: "ligesom", translation: "just as / like", note: "Comparison or simultaneity." },
]

export const CONJUNCTION_NOTES = [
  "After a subordinating conjunction, sentence adverbials (ikke, jo, da, vist) move BEFORE the verb: 'fordi jeg ikke kommer' — not 'fordi jeg kommer ikke'.",
  "Coordinating conjunctions (og, eller, men, for, så) keep normal main-clause word order on both sides.",
]

export function parseConjunctionsSentinel(selectedLemma: string): boolean {
  return selectedLemma === CONJUNCTIONS_SENTINEL
}

export const CONJUNCTION_LEMMAS = new Set(
  [...COORDINATING_CONJUNCTION_ROWS, ...SUBORDINATING_CONJUNCTION_ROWS].map((row) =>
    row.lemma.toLowerCase(),
  ),
)

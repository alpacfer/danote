export const PREPOSITIONS_SENTINEL = "__prepositions"

export type PrepositionEntry = {
  lemma: string
  translation: string
  note?: string
}

export const PREPOSITION_ROWS: PrepositionEntry[] = [
  { lemma: "i", translation: "in / for (duration)", note: "Location inside; also for a stretch of time: 'i to timer'." },
  { lemma: "på", translation: "on / at", note: "On a surface; also locations like 'på arbejde', 'på café'." },
  { lemma: "til", translation: "to / for", note: "Direction toward; also 'belonging to' and 'until' in time." },
  { lemma: "fra", translation: "from", note: "Origin, departure, or source." },
  { lemma: "med", translation: "with", note: "Accompaniment or instrument." },
  { lemma: "af", translation: "of / by / off", note: "Origin, agent, or material; 'lavet af' = made of." },
  { lemma: "over", translation: "over / above", note: "Above, across, or 'about' a topic." },
  { lemma: "under", translation: "under / during", note: "Beneath; also 'during' a time period." },
  { lemma: "for", translation: "for", note: "Purpose or recipient; 'for to dage siden' = two days ago." },
  { lemma: "om", translation: "about / in (future)", note: "Topic ('about something'); also 'in X time': 'om en uge'." },
  { lemma: "hos", translation: "at (someone's place)", note: "At a person's home or workplace: 'hos lægen'." },
  { lemma: "ved", translation: "by / next to", note: "Adjacent location; also 'by means of'." },
  { lemma: "mod", translation: "against / toward", note: "Opposition or direction toward." },
  { lemma: "gennem", translation: "through", note: "Through a space or a duration." },
  { lemma: "efter", translation: "after", note: "Sequence in time or space." },
  { lemma: "før", translation: "before", note: "Sequence in time." },
  { lemma: "mellem", translation: "between", note: "Between two or more entities." },
  { lemma: "uden", translation: "without", note: "Absence." },
  { lemma: "bag", translation: "behind", note: "Position behind something." },
  { lemma: "foran", translation: "in front of", note: "Position in front of something." },
  { lemma: "omkring", translation: "around / about", note: "Surrounding location or approximate quantity." },
]

export function parsePrepositionsSentinel(selectedLemma: string): boolean {
  return selectedLemma === PREPOSITIONS_SENTINEL
}

export const PREPOSITION_LEMMAS = new Set(PREPOSITION_ROWS.map((row) => row.lemma.toLowerCase()))

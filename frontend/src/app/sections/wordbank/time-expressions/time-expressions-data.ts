export const TIME_EXPRESSIONS_SENTINEL = "__time_expressions"

export type TimeExpressionRow = {
  lemma: string
  english: string
  note?: string
}

export const CLOCK_PHRASES: TimeExpressionRow[] = [
  { lemma: "Hvad er klokken?", english: "What time is it?" },
  { lemma: "Klokken er to.", english: "It's two o'clock." },
  { lemma: "Kvart over tre", english: "Quarter past three" },
  { lemma: "Halv fem", english: "Half past four (lit. 'half five')", note: "Watch out: 'halv fem' means 4:30, not 5:30. The hour is the *upcoming* hour." },
  { lemma: "Kvart i seks", english: "Quarter to six" },
  { lemma: "Ti minutter i syv", english: "Ten minutes to seven" },
]

export const RELATIVE_DAY_ROWS: TimeExpressionRow[] = [
  { lemma: "i går", english: "yesterday" },
  { lemma: "i dag", english: "today" },
  { lemma: "i morgen", english: "tomorrow" },
  { lemma: "i forgårs", english: "the day before yesterday" },
  { lemma: "i overmorgen", english: "the day after tomorrow" },
  { lemma: "i aftes", english: "last night" },
  { lemma: "i aften", english: "tonight" },
]

export const DURATION_ROWS: TimeExpressionRow[] = [
  { lemma: "for … siden", english: "ago", note: "'for to dage siden' = two days ago." },
  { lemma: "om …", english: "in (future)", note: "'om en uge' = in a week (from now)." },
  { lemma: "i …", english: "for (duration)", note: "'i to timer' = for two hours." },
  { lemma: "indtil …", english: "until" },
  { lemma: "siden …", english: "since" },
]

export const FREQUENCY_ROWS: TimeExpressionRow[] = [
  { lemma: "altid", english: "always" },
  { lemma: "ofte", english: "often" },
  { lemma: "nogle gange", english: "sometimes" },
  { lemma: "sjældent", english: "rarely" },
  { lemma: "aldrig", english: "never" },
]

export function parseTimeExpressionsSentinel(selectedLemma: string): boolean {
  return selectedLemma === TIME_EXPRESSIONS_SENTINEL
}

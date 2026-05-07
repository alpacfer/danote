export const DAYS_MONTHS_SEASONS_SENTINEL = "__days_months_seasons"

export type CalendarRow = { lemma: string; english: string }

export const DAYS_OF_WEEK: CalendarRow[] = [
  { lemma: "mandag", english: "Monday" },
  { lemma: "tirsdag", english: "Tuesday" },
  { lemma: "onsdag", english: "Wednesday" },
  { lemma: "torsdag", english: "Thursday" },
  { lemma: "fredag", english: "Friday" },
  { lemma: "lørdag", english: "Saturday" },
  { lemma: "søndag", english: "Sunday" },
]

export const MONTHS: CalendarRow[] = [
  { lemma: "januar", english: "January" },
  { lemma: "februar", english: "February" },
  { lemma: "marts", english: "March" },
  { lemma: "april", english: "April" },
  { lemma: "maj", english: "May" },
  { lemma: "juni", english: "June" },
  { lemma: "juli", english: "July" },
  { lemma: "august", english: "August" },
  { lemma: "september", english: "September" },
  { lemma: "oktober", english: "October" },
  { lemma: "november", english: "November" },
  { lemma: "december", english: "December" },
]

export const SEASONS: CalendarRow[] = [
  { lemma: "forår", english: "spring" },
  { lemma: "sommer", english: "summer" },
  { lemma: "efterår", english: "autumn / fall" },
  { lemma: "vinter", english: "winter" },
]

export function parseDaysMonthsSeasonsSentinel(selectedLemma: string): boolean {
  return selectedLemma === DAYS_MONTHS_SEASONS_SENTINEL
}

export const CALENDAR_LEMMAS = new Set(
  [...DAYS_OF_WEEK, ...MONTHS, ...SEASONS].map((row) => row.lemma.toLowerCase()),
)

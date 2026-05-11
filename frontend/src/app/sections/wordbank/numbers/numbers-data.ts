export const NUMBERS_SENTINEL = "__numbers"

const UNITS = ["nul", "en", "to", "tre", "fire", "fem", "seks", "syv", "otte", "ni"] as const
const TEENS: Record<number, string> = {
  10: "ti",
  11: "elleve",
  12: "tolv",
  13: "tretten",
  14: "fjorten",
  15: "femten",
  16: "seksten",
  17: "sytten",
  18: "atten",
  19: "nitten",
}
const TENS: Record<number, string> = {
  20: "tyve",
  30: "tredive",
  40: "fyrre",
  50: "halvtreds",
  60: "tres",
  70: "halvfjerds",
  80: "firs",
  90: "halvfems",
}
export const ENGLISH_CARDINALS: Record<number, string> = {
  0: "zero",
  1: "one",
  2: "two",
  3: "three",
  4: "four",
  5: "five",
  6: "six",
  7: "seven",
  8: "eight",
  9: "nine",
  10: "ten",
  11: "eleven",
  12: "twelve",
  13: "thirteen",
  14: "fourteen",
  15: "fifteen",
  16: "sixteen",
  17: "seventeen",
  18: "eighteen",
  19: "nineteen",
  20: "twenty",
  30: "thirty",
  40: "forty",
  50: "fifty",
  60: "sixty",
  70: "seventy",
  80: "eighty",
  90: "ninety",
}

export const BASIC_NUMBER_ROWS = [
  ...UNITS.map((word, number) => ({ number, word })),
  ...Object.entries(TEENS).map(([number, word]) => ({ number: Number(number), word })),
]

export const TENS_NUMBER_ROWS = Object.entries(TENS).map(([number, word]) => ({ number: Number(number), word }))

export const NUMBER_RULE_ROWS = [
  { pattern: "21–99", form: "unit + og + ten", example: "21 = enogtyve" },
  { pattern: "100", form: "hundrede", example: "100 = et hundrede / hundrede" },
  { pattern: "101–999", form: "hundreds + og + remainder", example: "342 = tre hundrede og toogfyrre" },
  { pattern: "1.000+", form: "thousands + tusind + remainder", example: "2.021 = to tusind og enogtyve" },
]

export type OrdinalNumberRow = {
  number: number
  cardinal: string
  ordinal: string
  english: string
}

export const ORDINAL_NUMBER_ROWS: OrdinalNumberRow[] = [
  { number: 1, cardinal: "en", ordinal: "første", english: "first" },
  { number: 2, cardinal: "to", ordinal: "anden", english: "second" },
  { number: 3, cardinal: "tre", ordinal: "tredje", english: "third" },
  { number: 4, cardinal: "fire", ordinal: "fjerde", english: "fourth" },
  { number: 5, cardinal: "fem", ordinal: "femte", english: "fifth" },
  { number: 6, cardinal: "seks", ordinal: "sjette", english: "sixth" },
  { number: 7, cardinal: "syv", ordinal: "syvende", english: "seventh" },
  { number: 8, cardinal: "otte", ordinal: "ottende", english: "eighth" },
  { number: 9, cardinal: "ni", ordinal: "niende", english: "ninth" },
  { number: 10, cardinal: "ti", ordinal: "tiende", english: "tenth" },
  { number: 11, cardinal: "elleve", ordinal: "ellevte", english: "eleventh" },
  { number: 12, cardinal: "tolv", ordinal: "tolvte", english: "twelfth" },
  { number: 13, cardinal: "tretten", ordinal: "trettende", english: "thirteenth" },
  { number: 20, cardinal: "tyve", ordinal: "tyvende", english: "twentieth" },
  { number: 30, cardinal: "tredive", ordinal: "tredivte", english: "thirtieth" },
  { number: 100, cardinal: "hundrede", ordinal: "hundrede", english: "hundredth" },
  { number: 1000, cardinal: "tusind", ordinal: "tusinde", english: "thousandth" },
]

export const ORDINAL_NUMBER_RULE = "Most ordinals add -(en)de to the cardinal: syv → syvende, ti → tiende. Irregulars: første (1st), anden (2nd), tredje (3rd), fjerde (4th)."

export function parseNumbersSentinel(selectedLemma: string): boolean {
  return selectedLemma === NUMBERS_SENTINEL
}

export function numberFromSearchQuery(query: string): number | null {
  const cleaned = query.trim().replace(/[.,\s]/gu, "")
  if (!/^\d+$/u.test(cleaned)) {
    return null
  }
  const value = Number(cleaned)
  if (!Number.isInteger(value) || value < 0 || value > 999999) {
    return null
  }
  return value
}

export function danishNumber(value: number): string {
  if (value < 10) return UNITS[value] ?? ""
  if (value < 20) return TEENS[value] ?? ""
  if (value < 100) {
    const ten = Math.floor(value / 10) * 10
    const unit = value % 10
    return unit === 0 ? TENS[ten] : `${UNITS[unit]}og${TENS[ten]}`
  }
  if (value < 1000) {
    const hundred = Math.floor(value / 100)
    const remainder = value % 100
    const prefix = hundred === 1 ? "et hundrede" : `${UNITS[hundred]} hundrede`
    return remainder === 0 ? prefix : `${prefix} og ${danishNumber(remainder)}`
  }
  const thousands = Math.floor(value / 1000)
  const remainder = value % 1000
  const prefix = thousands === 1 ? "et tusind" : `${danishNumber(thousands)} tusind`
  return remainder === 0 ? prefix : `${prefix} ${remainder < 100 ? "og " : ""}${danishNumber(remainder)}`
}

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

export const BASIC_NUMBER_ROWS = [
  ...UNITS.map((word, number) => ({ number, word })),
  ...Object.entries(TEENS).map(([number, word]) => ({ number: Number(number), word })),
]

export const TENS_NUMBER_ROWS = Object.entries(TENS).map(([number, word]) => ({ number: Number(number), word }))

export const NUMBER_RULE_ROWS = [
  { pattern: "21-99", form: "unit + og + ten", example: "21 = enogtyve" },
  { pattern: "100", form: "hundrede", example: "100 = et hundrede / hundrede" },
  { pattern: "101-999", form: "hundreds + og + remainder", example: "342 = tre hundrede og toogfyrre" },
  { pattern: "1.000+", form: "thousands + tusind + remainder", example: "2.021 = to tusind og enogtyve" },
]

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

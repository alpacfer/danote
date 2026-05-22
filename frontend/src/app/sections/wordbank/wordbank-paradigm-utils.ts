import type { LemmaDetailsResponse } from "@/app/core"
import {
  caseFromMorphology,
  definitenessFromMorphology,
  degreeFromMorphology,
  determinerWordTypeFromMorphology,
  numberFromMorphology,
  verbFormFromMorphology,
} from "@/app/core"

export type SurfaceForm = LemmaDetailsResponse["surface_forms"][number]

export type ParadigmCellEntry = {
  form: SurfaceForm
  label?: string
}

export type ParadigmCell = {
  row: string
  column: string
  entries: ParadigmCellEntry[]
}

export type ParadigmSupplementaryGroup = {
  label: string
  forms: SurfaceForm[]
}

export type ParadigmTableData = {
  rows: string[]
  columns: string[]
  cells: ParadigmCell[]
  supplementaryGroups: ParadigmSupplementaryGroup[]
}

export type FormGroup = {
  label: string
  forms: SurfaceForm[]
}

const PARADIGM_ROWS = ["Singular", "Plural"] as const
const PARADIGM_COLUMNS = ["Indefinite", "Definite"] as const
const VERB_PARADIGM_ROWS = ["Infinitive", "Present", "Past", "Imperative", "Past participle"] as const
const VERB_PARADIGM_COLUMNS = ["Form"] as const

export function buildNounParadigm(surfaceForms: SurfaceForm[]): ParadigmTableData | null {
  const cells = createEmptyCells()
  const genitiveForms: SurfaceForm[] = []
  const otherForms: SurfaceForm[] = []

  for (const form of surfaceForms) {
    if (caseFromMorphology(form.morphology) === "Genitive") {
      genitiveForms.push(form)
      continue
    }
    const number = numberFromMorphology(form.morphology)
    const definiteness = definitenessFromMorphology(form.morphology)
    if (number && definiteness) {
      pushUniqueEntry(findCell(cells, number, definiteness), { form })
      continue
    }
    otherForms.push(form)
  }

  if (filledCellCount(cells) < 1) {
    return null
  }

  return {
    rows: [...PARADIGM_ROWS],
    columns: [...PARADIGM_COLUMNS],
    cells,
    supplementaryGroups: [
      { label: "Genitive", forms: genitiveForms },
      { label: "Other forms", forms: otherForms },
    ].filter((group) => group.forms.length > 0),
  }
}

export function buildAdjectiveParadigm(surfaceForms: SurfaceForm[]): ParadigmTableData | null {
  const cells = createEmptyCells()
  const otherForms: SurfaceForm[] = []

  for (const form of surfaceForms) {
    const slots = adjectiveSlotsForForm(form)
    if (slots.length === 0) {
      otherForms.push(form)
      continue
    }
    let assigned = false
    for (const slot of slots) {
      assigned = true
      if (slot === "singular_indefinite_n_word") {
        pushUniqueEntry(findCell(cells, "Singular", "Indefinite"), { form, label: "n-word" })
      } else if (slot === "singular_indefinite_t_word") {
        pushUniqueEntry(findCell(cells, "Singular", "Indefinite"), { form, label: "t-word" })
      } else if (slot === "singular_definite") {
        pushUniqueEntry(findCell(cells, "Singular", "Definite"), { form })
      } else if (slot === "plural_shared") {
        pushUniqueEntry(findCell(cells, "Plural", "Indefinite"), { form })
        pushUniqueEntry(findCell(cells, "Plural", "Definite"), { form })
      }
    }
    if (!assigned) {
      otherForms.push(form)
    }
  }

  if (filledCellCount(cells) < 1) {
    return null
  }

  return {
    rows: [...PARADIGM_ROWS],
    columns: [...PARADIGM_COLUMNS],
    cells,
    supplementaryGroups: otherForms.length > 0 ? [{ label: "Other forms", forms: otherForms }] : [],
  }
}

export function buildVerbParadigm(surfaceForms: SurfaceForm[]): ParadigmTableData | null {
  const cells = VERB_PARADIGM_ROWS.map((row) => ({ row, column: "Form", entries: [] as ParadigmCellEntry[] }))
  const otherForms: SurfaceForm[] = []

  for (const form of surfaceForms) {
    const slots = verbSlotsForForm(form)
    if (slots.length === 0) {
      otherForms.push(form)
      continue
    }
    for (const slot of slots) {
      pushUniqueEntry(findCell(cells, slot, "Form"), { form })
    }
  }

  if (filledCellCount(cells) < 1) {
    return null
  }

  return {
    rows: [...VERB_PARADIGM_ROWS],
    columns: [...VERB_PARADIGM_COLUMNS],
    cells,
    supplementaryGroups: otherForms.length > 0 ? [{ label: "Other forms", forms: otherForms }] : [],
  }
}

const DEGREE_ORDER = ["Positive", "Comparative", "Superlative"]

export function buildAdjectiveDegreeGroups(surfaceForms: SurfaceForm[]): FormGroup[] {
  const groups = new Map<string, SurfaceForm[]>()
  const ungrouped: SurfaceForm[] = []

  for (const form of surfaceForms) {
    const label = degreeFromMorphology(form.morphology)
    if (label) {
      const list = groups.get(label) ?? []
      list.push(form)
      groups.set(label, list)
    } else {
      ungrouped.push(form)
    }
  }

  const sorted: FormGroup[] = DEGREE_ORDER
    .filter((label) => groups.has(label))
    .map((label) => ({ label, forms: groups.get(label)! }))

  if (ungrouped.length > 0) {
    sorted.push({ label: "Other", forms: ungrouped })
  }
  return sorted
}

function createEmptyCells(): ParadigmCell[] {
  return PARADIGM_ROWS.flatMap((row) => PARADIGM_COLUMNS.map((column) => ({ row, column, entries: [] })))
}

function findCell(cells: ParadigmCell[], row: string, column: string): ParadigmCell | undefined {
  return cells.find((cell) => cell.row === row && cell.column === column)
}

function pushUniqueEntry(cell: ParadigmCell | undefined, entry: ParadigmCellEntry): void {
  if (!cell) return
  const formKey = entry.form.form.trim().toLocaleLowerCase("da-DK")
  const exists = cell.entries.some(
    (existing) =>
      existing.label === entry.label &&
      existing.form.form.trim().toLocaleLowerCase("da-DK") === formKey,
  )
  if (exists) return
  cell.entries.push(entry)
}

function filledCellCount(cells: ParadigmCell[]): number {
  return cells.filter((cell) => cell.entries.length > 0).length
}

function adjectiveSlotsForForm(form: SurfaceForm): string[] {
  const slots = new Set<string>()
  for (const gram of splitGramRaw(form.gram_raw)) {
    if (!gram.startsWith("adj")) {
      continue
    }
    const parts = new Set(gram.split(".").map((part) => part.trim()).filter(Boolean))
    if (parts.has("sg") && parts.has("ubest") && parts.has("fk")) {
      slots.add("singular_indefinite_n_word")
    }
    if (parts.has("sg") && parts.has("ubest") && parts.has("itk")) {
      slots.add("singular_indefinite_t_word")
    }
    if (parts.has("sg") && parts.has("best")) {
      slots.add("singular_definite")
    }
    if (parts.has("pl")) {
      slots.add("plural_shared")
    }
  }
  if (slots.size > 0) {
    return [...slots]
  }

  const number = numberFromMorphology(form.morphology)
  const definiteness = definitenessFromMorphology(form.morphology)
  const wordType = determinerWordTypeFromMorphology(form.morphology)
  if (number === "Singular" && definiteness !== "Definite" && wordType === "n-word") {
    return ["singular_indefinite_n_word"]
  }
  if (number === "Singular" && definiteness !== "Definite" && wordType === "t-word") {
    return ["singular_indefinite_t_word"]
  }
  if (number === "Singular" && definiteness === "Definite") {
    return ["singular_definite", "plural_shared"]
  }
  if (number === "Plural") {
    return ["plural_shared"]
  }
  return []
}

function verbSlotsForForm(form: SurfaceForm): string[] {
  const slots = new Set<string>()
  for (const gram of splitGramRaw(form.gram_raw)) {
    if (!gram.startsWith("vb")) {
      continue
    }
    const parts = new Set(gram.split(".").map((part) => part.trim()).filter(Boolean))
    if (parts.has("imp")) {
      slots.add("Imperative")
    }
    if (parts.has("inf")) {
      slots.add("Infinitive")
    }
    if (parts.has("perf") && parts.has("part")) {
      slots.add("Past participle")
    }
    if (parts.has("præs") || parts.has("prs")) {
      slots.add("Present")
    }
    if (parts.has("præt")) {
      slots.add("Past")
    }
  }
  const label = verbFormFromMorphology(form.morphology)
  if (label) {
    return label === "Past" && slots.has("Imperative") ? ["Past", "Imperative"] : [label]
  }
  return slots.size > 0 ? [...slots] : []
}

function splitGramRaw(gramRaw: string | null | undefined): string[] {
  if (!gramRaw?.trim()) {
    return []
  }
  return gramRaw
    .split("|")
    .map((item) => item.trim().toLocaleLowerCase("da-DK"))
    .filter(Boolean)
}

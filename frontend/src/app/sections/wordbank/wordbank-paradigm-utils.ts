import type { LemmaDetailsResponse } from "@/app/core"
import {
  caseFromMorphology,
  definitenessFromMorphology,
  degreeFromMorphology,
  numberFromMorphology,
  verbFormFromMorphology,
} from "@/app/core"

export type SurfaceForm = LemmaDetailsResponse["surface_forms"][number]

export type NounParadigmCell = {
  row: string
  column: string
  forms: SurfaceForm[]
}

export type NounParadigm = {
  cells: NounParadigmCell[]
  genitiveForms: SurfaceForm[]
  unclassifiedForms: SurfaceForm[]
  rows: string[]
  columns: string[]
}

const NOUN_ROWS = ["Singular", "Plural"] as const
const NOUN_COLUMNS = ["Indefinite", "Definite"] as const

export function buildNounParadigm(surfaceForms: SurfaceForm[]): NounParadigm | null {
  const cells: NounParadigmCell[] = NOUN_ROWS.flatMap((row) =>
    NOUN_COLUMNS.map((col) => ({ row, column: col, forms: [] })),
  )
  const genitiveForms: SurfaceForm[] = []
  const unclassifiedForms: SurfaceForm[] = []

  for (const form of surfaceForms) {
    if (caseFromMorphology(form.morphology) === "Genitive") {
      genitiveForms.push(form)
      continue
    }
    const number = numberFromMorphology(form.morphology)
    const definiteness = definitenessFromMorphology(form.morphology)
    if (number && definiteness) {
      const cell = cells.find((c) => c.row === number && c.column === definiteness)
      cell?.forms.push(form)
    } else {
      unclassifiedForms.push(form)
    }
  }

  const filledCellCount = cells.filter((c) => c.forms.length > 0).length
  if (filledCellCount < 2) return null

  return { cells, genitiveForms, unclassifiedForms, rows: [...NOUN_ROWS], columns: [...NOUN_COLUMNS] }
}

export type FormGroup = {
  label: string
  forms: SurfaceForm[]
}

const VERB_FORM_ORDER = ["Infinitive", "Present", "Past (preterite)", "Past participle", "Imperative"]

export function buildVerbFormGroups(surfaceForms: SurfaceForm[]): FormGroup[] {
  const groups = new Map<string, SurfaceForm[]>()
  const ungrouped: SurfaceForm[] = []

  for (const form of surfaceForms) {
    const label = verbFormFromMorphology(form.morphology)
    if (label) {
      const list = groups.get(label) ?? []
      list.push(form)
      groups.set(label, list)
    } else {
      ungrouped.push(form)
    }
  }

  const sorted: FormGroup[] = VERB_FORM_ORDER
    .filter((label) => groups.has(label))
    .map((label) => ({ label, forms: groups.get(label)! }))

  if (ungrouped.length > 0) {
    sorted.push({ label: "Other", forms: ungrouped })
  }
  return sorted
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

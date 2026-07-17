const CATEGORY_BADGE_PALETTE = [
  "bg-indigo-100 text-indigo-950 border-indigo-300 dark:bg-indigo-950/40 dark:text-indigo-200 dark:border-indigo-800",
  "bg-violet-100 text-violet-950 border-violet-300 dark:bg-violet-950/40 dark:text-violet-200 dark:border-violet-800",
  "bg-fuchsia-100 text-fuchsia-950 border-fuchsia-300 dark:bg-fuchsia-950/40 dark:text-fuchsia-200 dark:border-fuchsia-800",
  "bg-rose-100 text-rose-950 border-rose-300 dark:bg-rose-950/40 dark:text-rose-200 dark:border-rose-800",
  "bg-pink-100 text-pink-950 border-pink-300 dark:bg-pink-950/40 dark:text-pink-200 dark:border-pink-800",
  "bg-cyan-100 text-cyan-950 border-cyan-300 dark:bg-cyan-950/40 dark:text-cyan-200 dark:border-cyan-800",
  "bg-sky-100 text-sky-950 border-sky-300 dark:bg-sky-950/40 dark:text-sky-200 dark:border-sky-800",
  "bg-teal-100 text-teal-950 border-teal-300 dark:bg-teal-950/40 dark:text-teal-200 dark:border-teal-800",
  "bg-emerald-100 text-emerald-950 border-emerald-300 dark:bg-emerald-950/40 dark:text-emerald-200 dark:border-emerald-800",
  "bg-green-100 text-green-950 border-green-300 dark:bg-green-950/40 dark:text-green-200 dark:border-green-800",
  "bg-lime-100 text-lime-950 border-lime-300 dark:bg-lime-950/40 dark:text-lime-200 dark:border-lime-800",
  "bg-yellow-100 text-yellow-950 border-yellow-300 dark:bg-yellow-950/40 dark:text-yellow-200 dark:border-yellow-800",
  "bg-amber-100 text-amber-950 border-amber-300 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-800",
  "bg-orange-100 text-orange-950 border-orange-300 dark:bg-orange-950/40 dark:text-orange-200 dark:border-orange-800",
  "bg-blue-100 text-blue-950 border-blue-300 dark:bg-blue-950/40 dark:text-blue-200 dark:border-blue-800",
  "bg-red-100 text-red-950 border-red-300 dark:bg-red-950/40 dark:text-red-200 dark:border-red-800",
]

function semanticCategoryPaletteIndex(label: string, paletteLength: number): number {
  let hash = 0
  for (let index = 0; index < label.length; index += 1) {
    hash = (hash * 31 + label.charCodeAt(index)) >>> 0
  }
  return hash % paletteLength
}

export function semanticCategoryBadgeClass(label: string): string {
  return CATEGORY_BADGE_PALETTE[semanticCategoryPaletteIndex(label, CATEGORY_BADGE_PALETTE.length)]
}

const CATEGORY_BADGE_PALETTE = [
  "bg-emerald-100 text-emerald-950 border-emerald-300",
  "bg-sky-100 text-sky-950 border-sky-300",
  "bg-amber-100 text-amber-950 border-amber-300",
  "bg-rose-100 text-rose-950 border-rose-300",
  "bg-teal-100 text-teal-950 border-teal-300",
  "bg-lime-100 text-lime-950 border-lime-300",
]

export function semanticCategoryBadgeClass(label: string): string {
  let hash = 0
  for (let index = 0; index < label.length; index += 1) {
    hash = (hash * 31 + label.charCodeAt(index)) >>> 0
  }
  return CATEGORY_BADGE_PALETTE[hash % CATEGORY_BADGE_PALETTE.length]
}

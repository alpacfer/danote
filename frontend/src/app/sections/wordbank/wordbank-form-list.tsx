import { badgesForSavedForm, corSecondaryBadgeClass, normalizeSearchWord, posBadgeClass } from "@/app/core"
import type { FormGroup, SurfaceForm } from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { WordbankPronunciationWord } from "@/app/sections/wordbank/wordbank-pronunciation-word"
import { Badge } from "@/components/ui/badge"
import { AudioLines, Loader2 } from "lucide-react"

type WordbankFormListProps = {
  groups: FormGroup[]
  fallbackForms: SurfaceForm[]
  parentPosTag: string | null
  parentBadgeLabels: Set<string>
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}

export function WordbankFormList({
  groups,
  fallbackForms,
  parentPosTag,
  parentBadgeLabels,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: WordbankFormListProps) {
  const hasGroups = groups.length > 0 && groups.some((g) => g.label !== "Other")

  if (!hasGroups && fallbackForms.length === 0 && groups.length === 0) {
    return null
  }

  const allForms = hasGroups ? [] : [...groups.flatMap((g) => g.forms), ...fallbackForms]

  return (
    <div className="space-y-2">
      {hasGroups ? (
        groups.map((group) => (
          <div key={group.label} className="flex items-baseline gap-3 py-1">
            <span className="text-muted-foreground w-28 shrink-0 text-xs font-medium">{group.label}</span>
            <div className="flex flex-wrap gap-x-3 gap-y-1">
              {group.forms.map((form) => (
                <FormListItem
                  key={form.form}
                  form={form}
                  parentPosTag={parentPosTag}
                  parentBadgeLabels={parentBadgeLabels}
                  showBadges={false}
                  pronunciationLoadingByForm={pronunciationLoadingByForm}
                  regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                  onPlayPronunciation={onPlayPronunciation}
                  onRegeneratePronunciation={onRegeneratePronunciation}
                />
              ))}
            </div>
          </div>
        ))
      ) : (
        <div className="divide-y divide-border/50">
          {allForms.map((form) => (
            <FormListItem
              key={form.form}
              form={form}
              parentPosTag={parentPosTag}
              parentBadgeLabels={parentBadgeLabels}
              showBadges
              pronunciationLoadingByForm={pronunciationLoadingByForm}
              regeneratingPronunciationByForm={regeneratingPronunciationByForm}
              onPlayPronunciation={onPlayPronunciation}
              onRegeneratePronunciation={onRegeneratePronunciation}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function FormListItem({
  form,
  parentPosTag,
  parentBadgeLabels,
  showBadges,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
}: {
  form: SurfaceForm
  parentPosTag: string | null
  parentBadgeLabels: Set<string>
  showBadges: boolean
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
}) {
  const normalizedForm = normalizeSearchWord(form.form)
  const isRegenerating = Boolean(regeneratingPronunciationByForm[normalizedForm])
  const formBadges = showBadges ? badgesForSavedForm(form).filter((b) => !parentBadgeLabels.has(b.label)) : []

  return (
    <div className="flex flex-wrap items-center gap-x-2 gap-y-1 py-2 first:pt-0">
      <WordbankPronunciationWord
        form={form.form}
        hasPronunciation={form.has_pronunciation ?? false}
        pronunciationLoadingByForm={pronunciationLoadingByForm}
        onPlayPronunciation={onPlayPronunciation}
        contextMenuItems={[
          {
            icon: isRegenerating ? <Loader2 className="animate-spin" /> : <AudioLines />,
            label: isRegenerating ? "Regenerating audio..." : "Regenerate audio",
            disabled: isRegenerating,
            onSelect: () => onRegeneratePronunciation(form.form),
          },
        ]}
        className="text-sm font-semibold"
        iconClassName="size-3"
      />
      {formBadges.map((badge) => (
        <Badge
          key={`${form.form}-badge-${badge.label}`}
          variant={badge.tone === "primary" ? "default" : "secondary"}
          className={`text-[11px] ${badge.tone === "primary" ? `border ${posBadgeClass(form.pos_tag ?? parentPosTag)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
          title={badge.tone === "primary" ? badge.label : undefined}
          aria-label={badge.tone === "primary" ? badge.label : undefined}
        >
          {badge.label}
        </Badge>
      ))}
    </div>
  )
}

import { posBadgeClass, primaryPosLabel } from "@/app/core"
import type { SpecimenTranslationGroup } from "@/app/sections/wordbank/wordbank-specimen-preview-data"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"

export function WordbankSpecimenPreview({
  posTags,
  translationGroups,
}: {
  posTags: string[]
  translationGroups: SpecimenTranslationGroup[]
}) {
  return (
    <div className="flex flex-col gap-3 p-4" data-wordbank-specimen-preview>
      <div className="flex min-h-6 items-start justify-between gap-3">
        <span className="min-w-0 flex-1" data-wordbank-specimen-title-slot />
        {posTags.length > 0 ? (
          <div className="flex flex-wrap justify-end gap-1">
            {posTags.map((posTag) => (
              <Badge
                key={posTag}
                variant="default"
                className={posBadgeClass(posTag)}
                title={primaryPosLabel(posTag) ?? posTag}
                aria-label={primaryPosLabel(posTag) ?? posTag}
              >
                {primaryPosLabel(posTag) ?? posTag}
              </Badge>
            ))}
          </div>
        ) : null}
      </div>
      {translationGroups.length > 0 ? (
        <div className="flex flex-col">
          {translationGroups.map((group, index) => (
            <div key={`${group.englishTranslation ?? "additional"}-${index}`}>
              {index > 0 ? <Separator className="my-3" /> : null}
              <TranslationGroup group={group} />
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function TranslationGroup({ group }: { group: SpecimenTranslationGroup }) {
  if (!group.englishTranslation) {
    return <p className="text-sm font-medium">{group.additionalTranslations.join(" · ")}</p>
  }
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm font-medium">{group.englishTranslation}</p>
      {group.additionalTranslations.length > 0 ? (
        <p className="text-muted-foreground text-sm italic">
          {group.additionalTranslations.join(" · ")}
        </p>
      ) : null}
    </div>
  )
}

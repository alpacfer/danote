import { SearchResultAction } from "@/app/chrome/sidebar/sidebar-search-presentation"
import { Badge } from "@/components/ui/badge"
import { CommandItem } from "@/components/ui/command"
import {
  normalizeSearchWord,
  posMaterialTone,
  primaryPosLabel,
  posBadgeClass,
  type ENPosGroup,
  type SearchFeedbackContext,
  type SearchSaveSeed,
} from "@/app/core"

type SidebarEnResultsProps = {
  enPosGroups: ENPosGroup[]
  originalQuery: string
  onAddWordFromSearch: (
    surfaceToken: string,
    lemmaCandidate: string | null,
    feedbackContext?: SearchFeedbackContext,
    metadata?: {
      posTag?: string | null
      morphology?: string | null
      corId?: string | null
    },
    searchSeed?: SearchSaveSeed | null,
  ) => Promise<string | null>
  onCloseSearch: () => void
}

export function SidebarEnResults({
  enPosGroups,
  originalQuery,
  onAddWordFromSearch,
  onCloseSearch,
}: SidebarEnResultsProps) {
  return (
    <>
      {enPosGroups.map((group) => {
        const displayWord = group.danish_translation?.trim() || group.lemma
        const normalizedDanish = normalizeSearchWord(group.danish_translation ?? "")
        const isSaveBlocked = !normalizedDanish
        const key = `${displayWord.toLowerCase()}-${group.lemma.toLowerCase()}-${group.pos_ud}`
        const topSense = group.senses[0]
        return (
          <CommandItem
            key={`search-en-${key}`}
            value={`en-${key}`}
            data-search-slip
            data-material="word"
            data-material-tone={posMaterialTone(group.pos_ud)}
            disabled={isSaveBlocked}
            onSelect={() => {
              if (isSaveBlocked) {
                return
              }
              void (async () => {
                const addedLemma = await onAddWordFromSearch(
                  normalizedDanish,
                  normalizedDanish,
                  {
                    rawToken: originalQuery,
                    predictedStatus: "new",
                    suggestionsShown: [`${group.lemma}:${group.pos_ud}`],
                  },
                  {
                    posTag: null,
                    morphology: null,
                    corId: null,
                  },
                  {
                    lemma: normalizedDanish,
                    surface: normalizedDanish,
                    dictionary_status: "generated_non_cor",
                    meaning_key: group.lemma,
                    gloss: topSense?.gloss ?? null,
                    english_translation: originalQuery || group.lemma,
                    pos_tag: group.pos_ud ?? null,
                    morphology: null,
                  },
                )
                if (addedLemma) {
                  onCloseSearch()
                }
              })()
            }}
            className="flex items-start justify-between gap-3"
          >
            <div className="flex min-w-0 flex-col items-start gap-0.5">
              <span>
                <strong data-search-lexical className="font-semibold">{displayWord}</strong>
              </span>
              {isSaveBlocked ? (
                <span className="text-muted-foreground text-xs leading-4">Translation required before saving.</span>
              ) : null}
              {group.meaning_description ? (
                <span className="text-muted-foreground text-xs leading-4">{group.meaning_description}</span>
              ) : null}
              <div className="mt-1 flex flex-wrap gap-1.5">
                <Badge
                  variant="default"
                  className={`text-xs border ${posBadgeClass(group.pos_ud)}`}
                  title={primaryPosLabel(group.pos_ud) ?? group.pos_ud}
                  aria-label={primaryPosLabel(group.pos_ud) ?? group.pos_ud}
                >
                  {primaryPosLabel(group.pos_ud) ?? group.pos_ud}
                </Badge>
              </div>
            </div>
            <SearchResultAction kind="add" muted={isSaveBlocked} />
          </CommandItem>
        )
      })}
    </>
  )
}

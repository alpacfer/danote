import type { LemmaDetailsResponse } from "@/app/core"
import {
  additionalTranslationsDisplay,
  corSecondaryBadgeClass,
  getMeaningVerificationGate,
  isMultiWordLemma,
  lemmaTranslationWithGloss,
  normalizeSearchWord,
  posBadgeClass,
  semanticCategoryBadgeClass,
} from "@/app/core"
import { WordbankFormList } from "@/app/sections/wordbank/wordbank-form-list"
import { wordPageBadgesForSavedForm } from "@/app/sections/wordbank/wordbank-card-badges"
import { applyPrimaryBadgeLabelOverride, primaryPosBadgeOverride } from "@/app/sections/wordbank/wordbank-primary-pos-badge"
import { WordbankParadigmTable } from "@/app/sections/wordbank/wordbank-paradigm-table"
import {
  buildPronunciationAvailabilityMap,
  hasPronunciationForForm,
  resolvePronunciationAvailability,
} from "@/app/sections/wordbank/wordbank-pronunciation-availability"
import { WordbankScopeContextMenu } from "@/app/sections/wordbank/wordbank-scope-context-menu"
import {
  buildAdjectiveDegreeGroups,
  buildAdjectiveParadigm,
  buildNounParadigm,
  buildVerbParadigm,
} from "@/app/sections/wordbank/wordbank-paradigm-utils"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent } from "@/components/ui/card"
import { ScrollableBadgeRow } from "@/components/ui/scrollable-badge-row"

type WordbankMeaningSectionsProps = {
  lemma: string
  lemmaSurfaceForms: LemmaDetailsResponse["surface_forms"]
  meaningSections: LemmaDetailsResponse["meaning_sections"]
  selectedMeaningId: number | null
  pronunciationLoadingByForm: Record<string, boolean>
  regeneratingPronunciationByForm: Record<string, boolean>
  onPlayPronunciation: (form: string) => void
  onRegeneratePronunciation: (form: string) => void
  isFindingAlternativeTranslations: boolean
  onFindAlternativeTranslations: (meaningId: number | null) => void
  isRethinkingCategories: boolean
  onRethinkCategories: (meaningId: number | null) => void
  isCompletingMeaningVariations: boolean
  onCompleteMeaningVariations: (meaningId: number | null) => void
  onRequestDeleteMeaning: (meaning: { id: number; label: string; translation: string | null }) => void
  generatingExampleByMeaningId: Record<number, boolean>
  onGenerateExample: (meaningId: number, tense?: import("@/app/core/morphology").VerbFormLabel) => void
  rerunningMeaningVerificationById: Record<number, boolean>
  onRerunMeaningVerification: (meaningId: number) => void
  onOpenPinnedTab?: (sentinel: string) => void
  onApplyFilterAndNavigateBack?: (type: "pos" | "category", value: string) => void
}

export function WordbankMeaningSections({
  lemma,
  lemmaSurfaceForms,
  meaningSections,
  selectedMeaningId,
  pronunciationLoadingByForm,
  regeneratingPronunciationByForm,
  onPlayPronunciation,
  onRegeneratePronunciation,
  isFindingAlternativeTranslations,
  onFindAlternativeTranslations,
  isRethinkingCategories,
  onRethinkCategories,
  isCompletingMeaningVariations,
  onCompleteMeaningVariations,
  onRequestDeleteMeaning,
  generatingExampleByMeaningId,
  onGenerateExample,
  rerunningMeaningVerificationById,
  onRerunMeaningVerification,
  onOpenPinnedTab,
  onApplyFilterAndNavigateBack,
}: WordbankMeaningSectionsProps) {
  if (!meaningSections || meaningSections.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved meanings for this lemma.</p>
  }

  return (
    <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
      {meaningSections.map((section) => {
        const sectionBadges = applyPrimaryBadgeLabelOverride(
          wordPageBadgesForSavedForm({
            pos_tag: section.pos_tag ?? null,
            morphology: section.morphology ?? null,
            gram_raw: section.gram_raw ?? null,
            // Pass the page-level lemma so MWE meaning cards render "Phrasal verb"
            // instead of "Verb". The section itself does not carry the lemma.
            lemma: lemma,
          }),
          { posTag: section.pos_tag ?? null, morphology: section.morphology ?? null, lemma },
        )
        const sectionPosBadgeOverride = primaryPosBadgeOverride({
          posTag: section.pos_tag ?? null,
          morphology: section.morphology ?? null,
          lemma,
        })
        const isGeneratedNonCor = section.dictionary_status === "generated_non_cor"
        const sectionTranslationBase = additionalTranslationsDisplay(
          section.english_translation ?? null,
          section.additional_translations ?? [],
        )
        const sectionTranslation = lemmaTranslationWithGloss(
          sectionTranslationBase,
          section.gloss_translation ?? null,
        )
        const completionGate = getMeaningVerificationGate(
          {
            lemma,
            english_translation: null,
            pos_tag: null,
            morphology: null,
            is_sectioned: true,
            meaning_sections: meaningSections,
            surface_forms: [],
          },
          section.id > 0 ? section.id : null,
        )
        const posTag = (section.pos_tag ?? "").toUpperCase()
        const isNoun = posTag === "NOUN"
        const isAdjective = posTag === "ADJ"
        const isVerb = posTag === "VERB"
        const meaningLemma = isVerb && section.id > 0 ? `at ${lemma}` : lemma
        const canCompleteParadigm = isNoun || isAdjective || isVerb
        const pronunciationAvailability = buildPronunciationAvailabilityMap([
          ...lemmaSurfaceForms,
          ...section.surface_forms,
        ])
        const resolvedSectionSurfaceForms = resolvePronunciationAvailability(
          section.surface_forms,
          pronunciationAvailability,
        )
        const lemmaHasPronunciation = hasPronunciationForForm(pronunciationAvailability, lemma)
        const lemmaSyntheticForm = {
          form: lemma,
          pos_tag: section.pos_tag ?? null,
          morphology: isVerb ? "VerbForm=Inf" : section.morphology ?? null,
          gram_raw: isVerb ? null : section.gram_raw ?? null,
          has_pronunciation: lemmaHasPronunciation,
        }
        const formsWithLemma = [lemmaSyntheticForm, ...resolvedSectionSurfaceForms]
        const nounParadigm = isNoun ? buildNounParadigm(formsWithLemma) : null
        const adjectiveParadigm = posTag === "ADJ" ? buildAdjectiveParadigm(formsWithLemma) : null
        const verbParadigm = isVerb ? buildVerbParadigm(formsWithLemma) : null
        const formGroups = posTag === "ADJ" ? buildAdjectiveDegreeGroups(formsWithLemma) : []
        const hasRenderableForms = Boolean(nounParadigm || adjectiveParadigm || verbParadigm || resolvedSectionSurfaceForms.length > 0)
        const sectionBadgeLabels = new Set(sectionBadges.map((b) => b.label))
        const actionMeaningId = section.id > 0 ? section.id : null
        const isRootSection = section.id === 0

        return (
          <WordbankScopeContextMenu
            key={`meaning-section-${section.id}-${section.meaning_key}`}
            isRerunningVerification={Boolean(rerunningMeaningVerificationById[section.id])}
            onRerunVerification={() => {
              if (actionMeaningId !== null) onRerunMeaningVerification(actionMeaningId)
            }}
            isFindingAlternativeTranslations={isFindingAlternativeTranslations}
            onFindAlternativeTranslations={() => onFindAlternativeTranslations(actionMeaningId)}
            isRethinkingCategories={isRethinkingCategories}
            onRethinkCategories={() => onRethinkCategories(actionMeaningId)}
            isGeneratingExample={Boolean(generatingExampleByMeaningId[section.id])}
            isVerb={isVerb}
            onGenerateExample={(tense) => {
              if (actionMeaningId !== null) onGenerateExample(actionMeaningId, tense)
            }}
            canCompleteVariations={canCompleteParadigm && !completionGate.isLocked}
            completeVariationsLabel={completionGate.label}
            isCompletingVariations={isCompletingMeaningVariations}
            onCompleteVariations={canCompleteParadigm ? () => onCompleteMeaningVariations(actionMeaningId) : undefined}
            onDeleteMeaning={actionMeaningId === null ? undefined : () => onRequestDeleteMeaning({
              id: actionMeaningId,
              label: meaningLemma,
              translation: sectionTranslation,
            })}
          >
            <Card
              id={`wordbank-meaning-${section.id}`}
              data-testid={section.id === 0 ? "wordbank-lemma-scope-card" : `wordbank-meaning-card-${section.id}`}
              data-meaning-id={section.id}
              data-selected={selectedMeaningId === section.id ? "true" : "false"}
              className="py-5"
            >
              <CardContent className="flex flex-col gap-3">
                {/* Row 1: Lemma + inline badges. Badges scroll horizontally when
                    they overflow the available width. Right padding reserves
                    space for the meatball menu (always visible on mobile, on
                    hover on desktop). */}
                <div className="flex flex-col gap-1.5">
                  <div className="flex items-center gap-2 pr-9">
                    <span
                      data-testid={isRootSection ? "wordbank-lemma-card-lemma" : `wordbank-meaning-card-lemma-${section.id}`}
                      className="shrink-0 text-lg leading-tight font-bold"
                    >
                      {meaningLemma}
                    </span>
                    {(sectionBadges.length > 0 || isGeneratedNonCor || (section.categories?.length ?? 0) > 0) ? (
                      <ScrollableBadgeRow
                        className="flex-1"
                        fadeFromClass="from-card"
                        testId={isRootSection ? "wordbank-lemma-header-badges" : `wordbank-meaning-badges-${section.id}`}
                      >
                        {isGeneratedNonCor ? (
                          <Badge
                            variant="outline"
                            className="shrink-0 text-xs border-amber-300 bg-amber-50 text-amber-800"
                          >
                            Not in COR
                          </Badge>
                        ) : null}
                        {sectionBadges.map((badge) => {
                          const isWordType = badge.tone === "primary"
                          const pinnedSentinel = isWordType ? sectionPosBadgeOverride?.pinnedSentinel ?? null : null
                          const isClickable = isWordType && Boolean(pinnedSentinel ? onOpenPinnedTab : onApplyFilterAndNavigateBack)
                          const handleClick = !isClickable
                            ? undefined
                            : pinnedSentinel
                              ? () => onOpenPinnedTab!(pinnedSentinel)
                              : () => onApplyFilterAndNavigateBack!("pos", isMultiWordLemma(lemma) ? (badge.label === "Phrasal verb" ? "PHRASAL_VERB" : "IDIOM") : section.pos_tag ?? "")

                          return (
                            <Badge
                              key={`meaning-section-${section.id}-badge-${badge.label}`}
                              variant={badge.tone === "primary" ? "default" : "secondary"}
                              className={`shrink-0 text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(section.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`} ${
                                isClickable ? "cursor-pointer hover:scale-105 transition-transform" : ""
                              }`.trim()}
                              onClick={handleClick}
                            >
                              {badge.label}
                            </Badge>
                          )
                        })}
                        {section.categories?.map((category) => {
                          const isClickable = Boolean(onApplyFilterAndNavigateBack)
                          const handleClick = isClickable
                            ? () => onApplyFilterAndNavigateBack!("category", category)
                            : undefined

                          return (
                            <Badge
                              key={`meaning-section-${section.id}-category-${category}`}
                              variant="outline"
                              className={`shrink-0 text-xs ${semanticCategoryBadgeClass(category)} ${
                                isClickable ? "cursor-pointer hover:scale-105 transition-transform" : ""
                              }`.trim()}
                              onClick={handleClick}
                            >
                              {category}
                            </Badge>
                          )
                        })}
                      </ScrollableBadgeRow>
                    ) : null}
                  </div>
                  {/* Row 2: Translation directly below the lemma */}
                  {sectionTranslation ? (
                    <span className="text-muted-foreground text-sm italic">{sectionTranslation}</span>
                  ) : null}
                </div>

                {/* Forms section */}
                {hasRenderableForms ? (
                  <div className="mt-2">
                    {nounParadigm || adjectiveParadigm || verbParadigm ? (
                      <WordbankParadigmTable
                        paradigm={nounParadigm ?? adjectiveParadigm ?? verbParadigm!}
                        pronunciationLoadingByForm={pronunciationLoadingByForm}
                        regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                        onPlayPronunciation={onPlayPronunciation}
                        onRegeneratePronunciation={onRegeneratePronunciation}
                        nonInteractiveForms={section.id === 0 ? new Set([normalizeSearchWord(lemma)]) : undefined}
                      />
                    ) : (
                        <WordbankFormList
                          groups={formGroups}
                          fallbackForms={formGroups.length === 0 ? resolvedSectionSurfaceForms : []}
                          parentPosTag={section.pos_tag ?? null}
                          parentBadgeLabels={sectionBadgeLabels}
                        pronunciationLoadingByForm={pronunciationLoadingByForm}
                        regeneratingPronunciationByForm={regeneratingPronunciationByForm}
                        onPlayPronunciation={onPlayPronunciation}
                        onRegeneratePronunciation={onRegeneratePronunciation}
                      />
                    )}
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </WordbankScopeContextMenu>
        )
      })}
    </div>
  )
}

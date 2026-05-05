import type { LemmaDetailsResponse } from "@/app/core"
import {
  additionalTranslationsDisplay,
  badgesForSavedForm,
  corSecondaryBadgeClass,
  getMeaningVerificationGate,
  lemmaTranslationWithGloss,
  posBadgeClass,
  semanticCategoryBadgeClass,
} from "@/app/core"
import { WordbankFormList } from "@/app/sections/wordbank/wordbank-form-list"
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
  generatingExampleByMeaningId: Record<number, boolean>
  onGenerateExample: (meaningId: number, tense?: import("@/app/core/morphology").VerbFormLabel) => void
  rerunningMeaningVerificationById: Record<number, boolean>
  onRerunMeaningVerification: (meaningId: number) => void
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
  generatingExampleByMeaningId,
  onGenerateExample,
  rerunningMeaningVerificationById,
  onRerunMeaningVerification,
}: WordbankMeaningSectionsProps) {
  const normalizedLemma = lemma.trim().toLocaleLowerCase("da-DK")

  if (!meaningSections || meaningSections.length === 0) {
    return <p className="text-muted-foreground text-sm">No saved meanings for this lemma.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {meaningSections.map((section) => {
        const sectionBadges = badgesForSavedForm({
          pos_tag: section.pos_tag ?? null,
          morphology: section.morphology ?? null,
          gram_raw: section.gram_raw ?? null,
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
          section.id,
        )
        const posTag = (section.pos_tag ?? "").toUpperCase()
        const isNoun = posTag === "NOUN"
        const isAdjective = posTag === "ADJ"
        const isVerb = posTag === "VERB"
        const meaningLemma = isVerb ? `at ${lemma}` : lemma
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
          morphology: section.morphology ?? null,
          gram_raw: section.gram_raw ?? null,
          has_pronunciation: lemmaHasPronunciation,
        }
        const formsWithLemma = [lemmaSyntheticForm, ...resolvedSectionSurfaceForms.filter(
          (f) => f.form.trim().toLocaleLowerCase("da-DK") !== normalizedLemma,
        )]
        const nounParadigm = isNoun ? buildNounParadigm(formsWithLemma) : null
        const adjectiveParadigm = posTag === "ADJ" ? buildAdjectiveParadigm(formsWithLemma) : null
        const verbParadigm = isVerb ? buildVerbParadigm(formsWithLemma) : null
        const formGroups = posTag === "ADJ" ? buildAdjectiveDegreeGroups(formsWithLemma) : []
        const hasRenderableForms = Boolean(nounParadigm || adjectiveParadigm || verbParadigm || resolvedSectionSurfaceForms.length > 0)
        const sectionBadgeLabels = new Set(sectionBadges.map((b) => b.label))

        return (
          <WordbankScopeContextMenu
            key={`meaning-section-${section.id}-${section.meaning_key}`}
            isRerunningVerification={Boolean(rerunningMeaningVerificationById[section.id])}
            onRerunVerification={() => onRerunMeaningVerification(section.id)}
            isFindingAlternativeTranslations={isFindingAlternativeTranslations}
            onFindAlternativeTranslations={() => onFindAlternativeTranslations(section.id)}
            isRethinkingCategories={isRethinkingCategories}
            onRethinkCategories={() => onRethinkCategories(section.id)}
            isGeneratingExample={Boolean(generatingExampleByMeaningId[section.id])}
            isVerb={isVerb}
            onGenerateExample={(tense) => onGenerateExample(section.id, tense)}
            canCompleteVariations={canCompleteParadigm && !completionGate.isLocked}
            completeVariationsLabel={completionGate.label}
            isCompletingVariations={isCompletingMeaningVariations}
            onCompleteVariations={canCompleteParadigm ? () => onCompleteMeaningVariations(section.id) : undefined}
          >
            <Card
              id={`wordbank-meaning-${section.id}`}
              data-testid={`wordbank-meaning-card-${section.id}`}
              data-meaning-id={section.id}
              data-selected={selectedMeaningId === section.id ? "true" : "false"}
              className="py-5"
            >
              <CardContent className="space-y-3">
                {/* Line 1: Lemma + translation | Category badges */}
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
                      <span className="text-lg leading-tight font-bold">{meaningLemma}</span>
                      {sectionTranslation ? (
                        <span className="text-muted-foreground text-sm italic">{sectionTranslation}</span>
                      ) : null}
                    </div>
                    {/* Line 2: POS + morphology badges */}
                    {sectionBadges.length > 0 ? (
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        {isGeneratedNonCor ? (
                          <Badge
                            variant="outline"
                            className="text-xs border-amber-300 bg-amber-50 text-amber-800"
                          >
                            Not in COR
                          </Badge>
                        ) : null}
                        {sectionBadges.map((badge) => (
                          <Badge
                            key={`meaning-section-${section.id}-badge-${badge.label}`}
                            variant={badge.tone === "primary" ? "default" : "secondary"}
                            className={`text-xs ${badge.tone === "primary" ? `border ${posBadgeClass(section.pos_tag ?? null)}` : `border ${corSecondaryBadgeClass(badge.label)}`}`.trim()}
                          >
                            {badge.label}
                          </Badge>
                        ))}
                      </div>
                    ) : isGeneratedNonCor ? (
                      <div className="mt-1.5 flex flex-wrap gap-1.5">
                        <Badge
                          variant="outline"
                          className="text-xs border-amber-300 bg-amber-50 text-amber-800"
                        >
                          Not in COR
                        </Badge>
                      </div>
                    ) : null}
                  </div>
                  {section.categories && section.categories.length > 0 ? (
                    <div
                      data-testid={`wordbank-meaning-category-badges-${section.id}`}
                      className="flex flex-wrap justify-end gap-1.5 sm:max-w-[45%]"
                    >
                      {section.categories.map((category) => (
                        <Badge
                          key={`meaning-section-${section.id}-category-${category}`}
                          variant="outline"
                          className={`text-xs ${semanticCategoryBadgeClass(category)}`.trim()}
                        >
                          {category}
                        </Badge>
                      ))}
                    </div>
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

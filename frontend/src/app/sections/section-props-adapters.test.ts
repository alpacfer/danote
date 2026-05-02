import { describe, expect, it, vi } from "vitest"

import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
import { buildNotesSectionProps } from "@/app/sections/notes-section-props"
import { buildSentencebankSectionProps } from "@/app/sections/sentencebank-section-props"
import { buildWordbankSectionProps } from "@/app/sections/wordbank-section-props"

describe("section prop adapters", () => {
  it("maps notes props to the section contract", () => {
    const savedNotes = [{ id: "1", name: "note", text: "hej", savedAt: "now", tokens: [], discoveredTokenMetadata: {}, generatedTranslationMap: {} }]

    const result = buildNotesSectionProps({
      savedNotes: savedNotes as never,
    })

    expect(result.savedNotes).toBe(savedNotes)
  })

  it("maps sentencebank props without alteration", () => {
    const sentences = [{ id: 1, source_text: "Hej", english_translation: "Hi" }]
    const openWordbankLemma = vi.fn()
    const openWordbankMeaning = vi.fn()
    const openSentence = vi.fn()
    const playPronunciation = vi.fn(async () => undefined)
    const playPronunciationSlowly = vi.fn(async () => undefined)
    const regeneratePronunciation = vi.fn(async () => undefined)

    const result = buildSentencebankSectionProps({
      sentencebankError: null,
      isSentencebankLoading: false,
      sentences: sentences as never,
      pronunciationLoadingBySentenceId: {},
      regeneratingPronunciationBySentenceId: {},
      openWordbankLemma,
      openWordbankMeaning,
      selectedSentenceId: 42,
      pendingSentence: null,
      openSentence,
      playPronunciation,
      playPronunciationSlowly,
      regeneratePronunciation,
    })

    expect(result.sentencebankError).toBeNull()
    expect(result.isSentencebankLoading).toBe(false)
    expect(result.sentences).toBe(sentences)
    expect(result.onOpenWordbankLemma).toBe(openWordbankLemma)
    expect(result.onOpenWordbankMeaning).toBe(openWordbankMeaning)
    expect(result.selectedSentenceId).toBe(42)
    expect(result.pendingSentence).toBeNull()
    expect(result.pronunciationLoadingBySentenceId).toEqual({})
    expect(result.regeneratingPronunciationBySentenceId).toEqual({})

    result.onOpenSentence(41)
    result.onPlayPronunciation(41)
    result.onPlayPronunciationSlowly(41)
    result.onRegeneratePronunciation(41)

    expect(openSentence).toHaveBeenCalledWith(41)

    return Promise.resolve().then(() => {
      expect(playPronunciation).toHaveBeenCalledWith(41)
      expect(playPronunciationSlowly).toHaveBeenCalledWith(41)
      expect(regeneratePronunciation).toHaveBeenCalledWith(41)
    })
  })

  it("builds wordbank props with safe async wrappers", async () => {
    const playPronunciation = vi.fn(async () => undefined)
    const regenerate = vi.fn(async () => undefined)
    const findAlternativeTranslations = vi.fn(async () => undefined)
    const rethinkCategories = vi.fn(async () => undefined)
    const completeMeaningVariations = vi.fn(async () => undefined)
    const apply = vi.fn(async () => undefined)
    const retry = vi.fn(async () => undefined)
    const rerun = vi.fn(async () => undefined)
    const revertChange = vi.fn(async () => undefined)
    const saveRelatedWordFromSearchSeed = vi.fn(async () => null)
    const openRelatedWordTarget = vi.fn()
    const openSentence = vi.fn()
    const markVisibleVerificationNotificationsAsRead = vi.fn()

    const result = buildWordbankSectionProps({
      selectedLemma: "bog",
      selectedMeaningId: 12,
      wordbankError: null,
      isWordbankLoading: false,
      lemmas: [],
      groupedWordbankLemmas: [],
      unreadWordbankLemmaCounts: new Map(),
      setSelectedLemma: vi.fn(),
      lemmaDetails: null,
      lemmaDetailsError: null,
      isLemmaDetailsLoading: false,
      showLemmaDetailsLoadingSkeleton: false,
      pronunciationLoadingByForm: {},
      regeneratingPronunciationByForm: {},
      playPronunciation,
      regeneratePronunciation: regenerate,
      isFindingAlternativeTranslations: false,
      findAlternativeTranslations,
      isRethinkingCategories: false,
      rethinkCategories,
      isCompletingMeaningVariations: false,
      completeMeaningVariations,
      verificationOverview: {
        targets: [],
        queuedCount: 0,
        verifiedCount: 0,
        reviewCount: 0,
        totalSuggestedActions: 0,
      },
      verificationChanges: [],
      isLoadingVerificationChanges: false,
      isApplyingVerificationChanges: false,
      isRetryingVerification: false,
      isRevertingVerificationChange: false,
      rerunningMeaningVerificationById: {},
      markVisibleVerificationNotificationsAsRead,
      applyVerificationAction: apply,
      retryVerificationTarget: retry,
      rerunMeaningVerification: rerun,
      revertVerificationChange: revertChange,
      saveRelatedWordFromSearchSeed,
      openRelatedWordTarget,
      openSentence,
    })

    result.onPlayPronunciation("bog")
    result.onRegeneratePronunciation("bog")
    result.onFindAlternativeTranslations(12)
    result.onRethinkCategories(12)
    result.onCompleteMeaningVariations(12)
    result.onMarkVisibleVerificationNotificationsAsRead()
    result.onApplyVerificationAction("bog::root::root", 0)
    result.onRetryVerificationTarget("bog::root::root")
    result.onRerunMeaningVerification(12)
    result.onRevertVerificationChange(4)

    await Promise.resolve()

    expect(playPronunciation).toHaveBeenCalledWith("bog")
    expect(regenerate).toHaveBeenCalledTimes(1)
    expect(findAlternativeTranslations).toHaveBeenCalledWith(12)
    expect(rethinkCategories).toHaveBeenCalledWith(12)
    expect(completeMeaningVariations).toHaveBeenCalledWith(12)
    expect(markVisibleVerificationNotificationsAsRead).toHaveBeenCalledTimes(1)
    expect(apply).toHaveBeenCalledTimes(1)
    expect(retry).toHaveBeenCalledTimes(1)
    expect(rerun).toHaveBeenCalledWith(12)
    expect(revertChange).toHaveBeenCalledWith(4)
    result.onOpenSentence?.(41)
    expect(openSentence).toHaveBeenCalledWith(41)
    expect(result.selectedMeaningId).toBe(12)
  })

  it("builds developer props and preserves callbacks", async () => {
    const saveDeveloperApiKeys = vi.fn(async () => undefined)
    const resetDatabase = vi.fn(async () => undefined)

    const result = buildDeveloperSectionProps({
      status: "connected",
      backendUrl: "http://127.0.0.1:8000",
      apiStatusItems: [],
      translationProvider: "deepl",
      developerTranslationAzureApiKey: "",
      developerTranslationAzureRegion: "",
      developerTranslationAzureEndpoint: "",
      developerTranslationDeeplApiKey: "",
      developerTranslationDeeplEndpoint: "",
      developerTtsAzureApiKey: "",
      developerTtsAzureRegion: "",
      developerTtsAzureEndpoint: "",
      developerGeminiApiKey: "",
      isSavingDeveloperApiKeys: false,
      isTestingTranslation: false,
      translationProbeResult: null,
      isTestingSpeech: false,
      speechProbeResult: null,
      isTestingGemini: false,
      geminiProbeResult: null,
      isResettingDatabase: false,
      setTranslationProvider: vi.fn(),
      setDeveloperTranslationAzureApiKey: vi.fn(),
      setDeveloperTranslationAzureRegion: vi.fn(),
      setDeveloperTranslationAzureEndpoint: vi.fn(),
      setDeveloperTranslationDeeplApiKey: vi.fn(),
      setDeveloperTranslationDeeplEndpoint: vi.fn(),
      setDeveloperTtsAzureApiKey: vi.fn(),
      setDeveloperTtsAzureRegion: vi.fn(),
      setDeveloperTtsAzureEndpoint: vi.fn(),
      setDeveloperGeminiApiKey: vi.fn(),
      saveDeveloperApiKeys,
      runTranslationProbe: vi.fn(async () => undefined),
      runSpeechProbe: vi.fn(async () => undefined),
      runGeminiProbe: vi.fn(async () => undefined),
      resetDatabase,
    })

    result.onSaveDeveloperApiKeys()
    result.onResetDatabase()
    await Promise.resolve()

    expect(result.badgeVariant).toBe("secondary")
    expect(saveDeveloperApiKeys).toHaveBeenCalledTimes(1)
    expect(resetDatabase).toHaveBeenCalledTimes(1)
  })
})

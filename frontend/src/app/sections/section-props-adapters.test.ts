import { describe, expect, it, vi } from "vitest"

import { NLP_MODEL_OPTIONS } from "@/app/core"
import { buildDeveloperSectionProps } from "@/app/sections/developer-section-props"
import { buildNotesSectionProps } from "@/app/sections/notes-section-props"
import { buildPlaygroundSectionProps } from "@/app/sections/playground-section-props"
import { buildSentencebankSectionProps } from "@/app/sections/sentencebank-section-props"
import { buildWordbankSectionProps } from "@/app/sections/wordbank-section-props"

describe("section prop adapters", () => {
  it("preserves playground props by reference", () => {
    const playgroundProps = { noteText: "hej" }

    const result = buildPlaygroundSectionProps({
      playgroundProps: playgroundProps as never,
    })

    expect(result).toBe(playgroundProps)
  })

  it("maps notes props to the section contract", () => {
    const savedNotes = [{ id: "1", name: "note", text: "hej", savedAt: "now", tokens: [], discoveredTokenMetadata: {}, generatedTranslationMap: {} }]
    const onOpenSavedNote = vi.fn()

    const result = buildNotesSectionProps({
      savedNotes: savedNotes as never,
      openSavedNoteInPlayground: onOpenSavedNote as never,
    })

    expect(result.savedNotes).toBe(savedNotes)
    expect(result.onOpenSavedNote).toBe(onOpenSavedNote)
  })

  it("maps sentencebank props without alteration", () => {
    const sentences = [{ id: "1", source_text: "Hej", english_translation: "Hi" }]

    const result = buildSentencebankSectionProps({
      sentencebankError: null,
      isSentencebankLoading: false,
      sentences: sentences as never,
    })

    expect(result).toEqual({
      sentencebankError: null,
      isSentencebankLoading: false,
      sentences,
    })
  })

  it("builds wordbank props with safe async wrappers", async () => {
    const playPronunciation = vi.fn(async () => undefined)
    const regenerate = vi.fn(async () => undefined)
    const apply = vi.fn(async () => undefined)

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
      playPronunciation,
      isRegeneratingLemmaPronunciation: false,
      regenerateSelectedLemmaPronunciation: regenerate,
      selectedLemmaVerificationError: null,
      selectedLemmaVerificationQueued: null,
      selectedLemmaVerificationSuccess: null,
      hasSuggestedVerificationActions: () => false,
      isApplyingVerificationChanges: false,
      applySelectedLemmaVerificationAction: apply,
    })

    result.onPlayPronunciation("bog")
    result.onRegenerateSelectedLemmaPronunciation()
    result.onApplySelectedLemmaVerificationAction(0)

    await Promise.resolve()

    expect(playPronunciation).toHaveBeenCalledWith("bog")
    expect(regenerate).toHaveBeenCalledTimes(1)
    expect(apply).toHaveBeenCalledTimes(1)
    expect(result.selectedMeaningId).toBe(12)
  })

  it("builds developer props and preserves callbacks", async () => {
    const saveDeveloperApiKeys = vi.fn(async () => undefined)
    const resetDatabase = vi.fn(async () => undefined)

    const result = buildDeveloperSectionProps({
      status: "connected",
      backendUrl: "http://127.0.0.1:8000",
      apiStatusItems: [],
      selectedNlpModel: NLP_MODEL_OPTIONS[0],
      developerTranslationAzureApiKey: "",
      developerTranslationAzureRegion: "",
      developerTranslationAzureEndpoint: "",
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
      setSelectedNlpModel: vi.fn(),
      setDeveloperTranslationAzureApiKey: vi.fn(),
      setDeveloperTranslationAzureRegion: vi.fn(),
      setDeveloperTranslationAzureEndpoint: vi.fn(),
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

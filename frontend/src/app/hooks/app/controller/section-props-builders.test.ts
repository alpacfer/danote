import { describe, expect, it, vi } from "vitest"

import { buildDeveloperSectionProps } from "@/app/hooks/app/controller/build-developer-section-props"
import { buildPlaygroundSectionProps } from "@/app/hooks/app/controller/build-playground-section-props"
import { buildWordbankSectionProps } from "@/app/hooks/app/controller/build-wordbank-section-props"

describe("section props builders", () => {
  it("builds playground section context without altering references", () => {
    const playgroundProps = { noteText: "hej" }
    const savedNotes = [{ id: "1", name: "note", text: "hej", updatedAt: "now", tokens: [], discoveredTokenMetadata: {}, generatedTranslationMap: {} }]
    const onOpenSavedNote = vi.fn()

    const result = buildPlaygroundSectionProps({
      autosaveStatus: "saved",
      playgroundProps: playgroundProps as never,
      savedNotes: savedNotes as never,
      openSavedNoteInPlayground: onOpenSavedNote as never,
    })

    expect(result.autosaveStatus).toBe("saved")
    expect(result.playgroundProps).toBe(playgroundProps)
    expect(result.savedNotes).toBe(savedNotes)
    expect(result.openSavedNoteInPlayground).toBe(onOpenSavedNote)
  })

  it("builds wordbank section context with expected keys", async () => {
    const playPronunciation = vi.fn(async () => undefined)
    const regenerate = vi.fn(async () => undefined)
    const apply = vi.fn(async () => undefined)

    const result = buildWordbankSectionProps({
      selectedLemma: "bog",
      wordbankError: null,
      isWordbankLoading: false,
      lemmas: [],
      groupedWordbankLemmas: [],
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
      hasSuggestedVerificationChanges: false,
      isApplyingVerificationChanges: false,
      applySelectedLemmaVerificationChanges: apply,
      sentencebankError: null,
      isSentencebankLoading: false,
      sentences: [],
    })

    await result.playPronunciation("bog")
    await result.regenerateSelectedLemmaPronunciation()
    await result.applySelectedLemmaVerificationChanges()

    expect(playPronunciation).toHaveBeenCalledWith("bog")
    expect(regenerate).toHaveBeenCalled()
    expect(apply).toHaveBeenCalled()
  })

  it("builds developer section context preserving callbacks", async () => {
    const saveDeveloperApiKeys = vi.fn(async () => undefined)
    const resetDatabase = vi.fn(async () => undefined)

    const result = buildDeveloperSectionProps({
      status: "connected",
      backendUrl: "http://127.0.0.1:8000",
      apiStatusItems: [],
      selectedNlpModel: "none",
      developerTranslationAzureApiKey: "",
      developerTranslationAzureRegion: "",
      developerTranslationAzureEndpoint: "",
      developerTtsAzureApiKey: "",
      developerTtsAzureRegion: "",
      developerTtsAzureEndpoint: "",
      developerVerificationGeminiApiKey: "",
      isSavingDeveloperApiKeys: false,
      isResettingDatabase: false,
      setSelectedNlpModel: vi.fn(),
      setDeveloperTranslationAzureApiKey: vi.fn(),
      setDeveloperTranslationAzureRegion: vi.fn(),
      setDeveloperTranslationAzureEndpoint: vi.fn(),
      setDeveloperTtsAzureApiKey: vi.fn(),
      setDeveloperTtsAzureRegion: vi.fn(),
      setDeveloperTtsAzureEndpoint: vi.fn(),
      setDeveloperVerificationGeminiApiKey: vi.fn(),
      saveDeveloperApiKeys,
      resetDatabase,
    })

    await result.saveDeveloperApiKeys()
    await result.resetDatabase()

    expect(saveDeveloperApiKeys).toHaveBeenCalledTimes(1)
    expect(resetDatabase).toHaveBeenCalledTimes(1)
  })
})

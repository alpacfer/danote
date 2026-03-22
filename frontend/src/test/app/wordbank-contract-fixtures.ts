import type { AddWordResponse, LemmaDetailsResponse } from "@/app/core"

export function cloneContractFixture<T>(fixture: T): T {
  return structuredClone(fixture)
}

export const bogVariationGlossWordPageContractFixture = {
  lemma: "bog",
  english_translation: "book",
  pos_tag: "NOUN",
  morphology: "Gender=Com|Number=Sing|Definite=Ind",
  is_sectioned: false,
  categories: ["Food", "Household Objects"],
  surface_forms: [
    {
      form: "bogen",
      lemma: "bog",
      lemma_translation: "book",
      gloss: "til læsning",
      gloss_translation: "for reading",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Def",
      has_pronunciation: true,
    },
  ],
} satisfies LemmaDetailsResponse

export const bogHomographWordPageContractFixture = {
  lemma: "bog",
  english_translation: null,
  pos_tag: null,
  morphology: null,
  is_sectioned: true,
  meaning_sections: [
    {
      id: 1,
      meaning_key: "for-reading",
      gloss: "til læsning",
      english_translation: "book",
      gloss_translation: "for reading",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      categories: ["Household Objects"],
      surface_forms: [],
    },
    {
      id: 2,
      meaning_key: "beechmast",
      gloss: "frugt fra et bøgetræ",
      english_translation: "beechmast",
      gloss_translation: "fruit from a beech tree",
      pos_tag: "NOUN",
      morphology: "Gender=Neut|Number=Sing|Definite=Ind",
      categories: ["Food", "Plants"],
      surface_forms: [],
    },
  ],
  surface_forms: [],
} satisfies LemmaDetailsResponse

export const morHomographWordPageContractFixture = {
  lemma: "mor",
  english_translation: null,
  pos_tag: null,
  morphology: null,
  is_sectioned: true,
  meaning_sections: [
    {
      id: 1,
      meaning_key: "person",
      gloss: "person",
      english_translation: "mother",
      gloss_translation: "person",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      categories: ["Family", "People"],
      surface_forms: [],
    },
    {
      id: 2,
      meaning_key: "soil-layer",
      gloss: "jordlag",
      english_translation: "mother",
      gloss_translation: "soil layer",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      categories: ["Nature"],
      surface_forms: [],
    },
  ],
  surface_forms: [],
} satisfies LemmaDetailsResponse

export const teacherSectionedWordPageContractFixture = {
  lemma: "lærer",
  english_translation: "teacher",
  pos_tag: "NOUN",
  morphology: "Gender=Com|Number=Sing|Definite=Ind",
  is_sectioned: true,
  meaning_sections: [
    {
      id: 1,
      meaning_key: "teacher",
      gloss: "teacher",
      english_translation: "teacher",
      pos_tag: "NOUN",
      morphology: "Gender=Com|Number=Sing|Definite=Ind",
      categories: ["People", "School", "Work"],
      surface_forms: [
        {
          form: "lærere",
          gloss: "teacher",
          pos_tag: "NOUN",
          morphology: "Gender=Com|Number=Plur|Definite=Ind",
          has_pronunciation: false,
        },
      ],
    },
  ],
  surface_forms: [],
} satisfies LemmaDetailsResponse

export const teacherQueuedWordPageContractFixture = {
  ...teacherSectionedWordPageContractFixture,
  meaning_sections: [
    {
      ...teacherSectionedWordPageContractFixture.meaning_sections[0],
      verification: {
        status: "queued",
        provider: "gemini",
        reviewer_role: "Professional Danish Language Expert",
        message: "Word verification queued.",
        composed_word_count: null,
        stored_surface_form: "lærere",
        requested_at: "2026-03-13T12:00:00.000Z",
        suggested_actions: [],
      },
    },
  ],
} satisfies LemmaDetailsResponse

export const teacherVerifiedWordPageContractFixture = {
  ...teacherSectionedWordPageContractFixture,
  meaning_sections: [
    {
      ...teacherSectionedWordPageContractFixture.meaning_sections[0],
      verification: {
        status: "verified",
        provider: "gemini",
        reviewer_role: "Professional Danish Language Expert",
        message: "Verification passed.",
        composed_word_count: null,
        stored_surface_form: "lærere",
        requested_at: "2026-03-13T12:00:00.000Z",
        completed_at: "2026-03-13T12:00:03.000Z",
        suggested_actions: [],
      },
    },
  ],
} satisfies LemmaDetailsResponse

export const teacherQueuedSearchAddResponseContractFixture = {
  status: "inserted",
  stored_lemma: "lærer",
  stored_surface_form: "lærere",
  source: "manual",
  message: "Added 'lærer' to wordbank.",
  queued_pronunciation_forms: ["lærer", "lærere"],
  meaning: {
    id: 1,
    meaning_key: "teacher",
    gloss: "teacher",
    english_translation: "teacher",
  },
  saved_snapshot: teacherQueuedWordPageContractFixture,
} satisfies AddWordResponse

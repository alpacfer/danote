import { describe, expect, it } from "vitest"

import { buildEnTranslatedCorResults } from "@/app/chrome/sidebar/sidebar-search-query"
import type { CORSearchFormResponse } from "@/app/core"
import type { EnResolveResult } from "@/app/chrome/sidebar/sidebar-search-types"

function lortPayload(): CORSearchFormResponse {
  return {
    form: "lort",
    groups: [
      {
        lemma: "lort",
        gloss: "afføring; noget dårligt",
        pos_tag: "NOUN",
        variants: [
          {
            cor_id: "COR.LORT.SHIT",
            form: "lort",
            lemma: "lort",
            gloss: "afføring; noget dårligt",
            gloss_translation: "feces; something bad",
            lemma_translation: "shit",
            saveable_translation: "shit",
            gram_raw: "sb.fk.sg.ubest",
            norm: "N",
            lemma_idx: 1,
            gram_code: 110,
            variation: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Com|Number=Sing|Definite=Ind",
            features: { Gender: "Com", Number: "Sing", Definite: "Ind" },
            extra_tags: [],
          },
        ],
      },
      {
        lemma: "lort",
        gloss: "møg, skidt",
        pos_tag: "NOUN",
        variants: [
          {
            cor_id: "COR.LORT.CRAP",
            form: "lort",
            lemma: "lort",
            gloss: "møg, skidt",
            gloss_translation: "crap",
            lemma_translation: "crap",
            saveable_translation: "crap",
            gram_raw: "sb.itk.sg.ubest",
            norm: "N",
            lemma_idx: 2,
            gram_code: 120,
            variation: 1,
            pos_tag: "NOUN",
            morphology: "Gender=Neut|Number=Sing|Definite=Ind",
            features: { Gender: "Neut", Number: "Sing", Definite: "Ind" },
            extra_tags: [],
          },
        ],
      },
    ],
  }
}

function loebePayload(): CORSearchFormResponse {
  return {
    form: "løbe",
    groups: [
      {
        lemma: "løbe",
        gloss: "få mælk til at oste",
        pos_tag: "VERB",
        variants: [
          {
            cor_id: "COR.30574.200.01",
            form: "løbe",
            lemma: "løbe",
            gloss: "få mælk til at oste",
            gloss_translation: "make milk curdle",
            lemma_translation: "curdle",
            saveable_translation: "curdle",
            gram_raw: "vb.inf.akt",
            norm: "N",
            lemma_idx: 30574,
            gram_code: 200,
            variation: 1,
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            features: { VerbForm: "Inf", Voice: "Act" },
            extra_tags: [],
          },
        ],
      },
      {
        lemma: "løbe",
        gloss: "bevæge sig i løb",
        pos_tag: "VERB",
        variants: [
          {
            cor_id: "COR.30653.200.01",
            form: "løbe",
            lemma: "løbe",
            gloss: "bevæge sig i løb",
            gloss_translation: "move with a run",
            lemma_translation: "move",
            saveable_translation: "move",
            gram_raw: "vb.inf.akt",
            norm: "N",
            lemma_idx: 30653,
            gram_code: 200,
            variation: 1,
            pos_tag: "VERB",
            morphology: "VerbForm=Inf|Voice=Act",
            features: { VerbForm: "Inf", Voice: "Act" },
            extra_tags: [],
          },
        ],
      },
    ],
  }
}

describe("buildEnTranslatedCorResults", () => {
  it("keeps one COR row per Danish form and prefers the variant matching the English query", () => {
    const activeEnResolveResult: EnResolveResult = {
      query: "shit",
      groups: [
        {
          lemma: "shit",
          pos_ud: "NOUN",
          pos_raw: "noun",
          danish_translation: "lort",
          meaning_description: "feces or low quality",
          senses: [],
        },
      ],
    }

    const result = buildEnTranslatedCorResults(activeEnResolveResult, { lort: lortPayload() }, "shit")

    expect(result.corSearchVariantsToRender).toHaveLength(2)
    expect(result.corSearchVariantsToRender[0].variant.cor_id).toBe("COR.LORT.SHIT")
    expect(result.corSearchVariantsToRender[0].variant.english_source_description).toBe("feces or low quality")
    expect(result.corSearchVariantsToRender[1].variant.cor_id).toBe("COR.LORT.CRAP")
  })

  it("keeps distinct COR senses for the same Danish form and ranks by gloss-translation match", () => {
    const activeEnResolveResult: EnResolveResult = {
      query: "run",
      groups: [
        {
          lemma: "run",
          pos_ud: "VERB",
          pos_raw: "verb",
          danish_translation: "løbe",
          meaning_description: null,
          senses: [],
        },
      ],
    }

    const result = buildEnTranslatedCorResults(activeEnResolveResult, { løbe: loebePayload() }, "run")

    expect(result.corSearchVariantsToRender).toHaveLength(2)
    expect(result.corSearchVariantsToRender[0].variant.cor_id).toBe("COR.30653.200.01")
    expect(result.corSearchVariantsToRender[0].variant.gloss_translation).toBe("move with a run")
    expect(result.corSearchVariantsToRender[1].variant.cor_id).toBe("COR.30574.200.01")
    expect(result.corSearchVariantsToRender[1].variant.gloss_translation).toBe("make milk curdle")
  })

  it("preserves insertion order when no variant matches the English query", () => {
    const activeEnResolveResult: EnResolveResult = {
      query: "sprint",
      groups: [
        {
          lemma: "sprint",
          pos_ud: "VERB",
          pos_raw: "verb",
          danish_translation: "løbe",
          meaning_description: null,
          senses: [],
        },
      ],
    }

    const result = buildEnTranslatedCorResults(activeEnResolveResult, { løbe: loebePayload() }, "sprint")

    expect(result.corSearchVariantsToRender).toHaveLength(2)
    expect(result.corSearchVariantsToRender[0].variant.cor_id).toBe("COR.30574.200.01")
    expect(result.corSearchVariantsToRender[1].variant.cor_id).toBe("COR.30653.200.01")
  })
})

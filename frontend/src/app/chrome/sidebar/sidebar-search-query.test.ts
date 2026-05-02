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

    expect(result.corSearchVariantsToRender).toHaveLength(1)
    expect(result.corSearchVariantsToRender[0].variant.cor_id).toBe("COR.LORT.SHIT")
    expect(result.corSearchVariantsToRender[0].variant.english_source_description).toBe("feces or low quality")
  })
})

import { badgesForSavedForm } from "@/app/core"

describe("Wordbank saved badges", () => {
  it("maps adjective agreement to n-word labels instead of Common", () => {
    expect(
      badgesForSavedForm({
        pos_tag: "ADJ",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
      }).map((badge) => badge.label),
    ).toEqual(["Adjective", "n-word", "Singular", "Indefinite"])
  })

  it("parses API-serialized gram_raw with spaces around periods", () => {
    expect(
      badgesForSavedForm({
        pos_tag: "ADJ",
        morphology: "Gender=Com|Number=Sing|Definite=Ind",
        gram_raw: "adj. sg. ubest. fk | adj. sg. ubest. itk | adj. sg. best | adj. pl",
      }).map((badge) => badge.label),
    ).toEqual(["Adjective", "Singular", "Indefinite", "n-word", "t-word", "Definite", "Plural"])
  })

  it("keeps verb voice badges when morphology includes them", () => {
    expect(
      badgesForSavedForm({
        pos_tag: "VERB",
        morphology: "Tense=Pres|VerbForm=Fin|Voice=Act",
      }).map((badge) => badge.label),
    ).toEqual(["Verb", "Present", "Active"])
  })

  it("adds determiner definiteness badges from saved morphology", () => {
    expect(
      badgesForSavedForm({
        pos_tag: "DET",
        morphology: "Gender=Com|Number=Sing|Definite=Def",
      }).map((badge) => badge.label),
    ).toEqual(["Determiner", "n-word", "Singular", "Definite"])
  })
})

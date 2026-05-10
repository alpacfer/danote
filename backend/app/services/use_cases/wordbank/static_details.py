from __future__ import annotations

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.use_cases.static_hv_words import (
    StaticHvWord,
    static_hv_word_for_token,
)
from app.services.use_cases.static_presaved_words import (
    StaticPresavedWord,
    static_presaved_word_for_token,
)
from app.services.use_cases.static_pronouns import (
    StaticPronoun,
    static_pronoun_for_token,
)


def static_builtin_lemma_details(original_lemma: str, normalized_lemma: str) -> LemmaDetailsResponse | None:
    static_word: StaticPresavedWord | StaticHvWord | StaticPronoun | None
    if original_lemma.strip() == "I":
        static_word = static_pronoun_for_token("i")
    else:
        static_word = (
            static_presaved_word_for_token(normalized_lemma)
            or static_hv_word_for_token(normalized_lemma)
            or static_pronoun_for_token(normalized_lemma)
        )
    if static_word is None:
        return None

    return LemmaDetailsResponse(
        lemma=static_word.lemma,
        dictionary_status="unknown",
        english_translation=static_word.english_translation,
        additional_translations=[],
        pos_tag=static_word.pos_tag,
        morphology=static_word.morphology,
        is_sectioned=False,
        categories=[],
        verification=None,
        meaning_sections=[],
        surface_forms=[
            LemmaDetailsResponse.SurfaceFormDetails(
                form=static_word.lemma,
                pos_tag=static_word.pos_tag,
                morphology=static_word.morphology,
                lemma=static_word.lemma,
                lemma_translation=static_word.english_translation,
                has_pronunciation=True,
            )
        ],
        related_words=LemmaDetailsResponse.RelatedWordsSection(status="empty", items=[]),
        linked_sentences=[],
    )

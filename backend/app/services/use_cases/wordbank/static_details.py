from __future__ import annotations

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.use_cases.static_builtin_words import (
    StaticBuiltinSense,
    static_builtin_senses_for_token,
)
from app.services.use_cases.static_pronouns import static_pronoun_for_token


def static_builtin_lemma_details(original_lemma: str, normalized_lemma: str) -> LemmaDetailsResponse | None:
    if original_lemma.strip() == "I":
        formal = static_pronoun_for_token("i")
        static_senses = (
            StaticBuiltinSense(
                lemma=formal.lemma,
                meaning_key="pronoun",
                english_translation=formal.english_translation,
                pos_tag=formal.pos_tag,
                morphology=formal.morphology,
                provider="static_pronoun",
            ),
        ) if formal is not None else ()
    else:
        static_senses = static_builtin_senses_for_token(normalized_lemma)
    if not static_senses:
        return None
    if len(static_senses) > 1:
        return _sectioned_static_builtin_details(static_senses)

    static_word = static_senses[0]

    return LemmaDetailsResponse(
        lemma=static_word.lemma,
        dictionary_status="unknown",
        english_translation=static_word.english_translation,
        additional_translations=[],
        pos_tag=static_word.pos_tag,
        morphology=static_word.morphology,
        is_sectioned=False,
        categories=[],
        reference_links=_schema_reference_links(static_word.reference_links),
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


def _sectioned_static_builtin_details(static_senses: tuple[StaticBuiltinSense, ...]) -> LemmaDetailsResponse:
    lemma = static_senses[0].lemma
    return LemmaDetailsResponse(
        lemma=lemma,
        dictionary_status="unknown",
        english_translation=None,
        additional_translations=[],
        pos_tag=None,
        morphology=None,
        is_sectioned=True,
        categories=[],
        verification=None,
        meaning_sections=[
            LemmaDetailsResponse.MeaningSection(
                id=index,
                meaning_key=sense.meaning_key,
                dictionary_status="unknown",
                gloss=None,
                english_translation=sense.english_translation,
                additional_translations=[],
                gloss_translation=None,
                pos_tag=sense.pos_tag,
                morphology=sense.morphology,
                categories=[],
                reference_links=_schema_reference_links(sense.reference_links),
                verification=None,
                surface_forms=[],
            )
            for index, sense in enumerate(static_senses, start=1)
        ],
        surface_forms=[
            LemmaDetailsResponse.SurfaceFormDetails(
                form=lemma,
                pos_tag=None,
                morphology=None,
                lemma=lemma,
                lemma_translation=None,
                has_pronunciation=True,
            )
        ],
        related_words=LemmaDetailsResponse.RelatedWordsSection(status="empty", items=[]),
        linked_sentences=[],
    )


def _schema_reference_links(reference_links):
    return [
        LemmaDetailsResponse.ReferenceLink(
            page_id=link.page_id,
            page_title=link.page_title,
            tab_id=link.tab_id,
            tab_title=link.tab_title,
            sentinel=link.sentinel,
        )
        for link in reference_links
    ]

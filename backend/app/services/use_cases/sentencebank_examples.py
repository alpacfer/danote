from __future__ import annotations

from app.api.schemas.v1.sentencebank import GenerateExamplePreviewResponse
from app.services.gemini_translation import ExampleSentenceGenerationInput
from app.services.token_classifier import normalize_token
from app.services.use_cases.sentencebank_text import normalize_sentence_text
from app.services.use_cases.static_hv_words import static_hv_word_for_token
from app.services.use_cases.wordbank.gloss_translations import meaning_gloss_translation
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def _normalize_generated_source_text(value: str) -> str:
    source_text = normalize_sentence_text(value).rstrip(".").strip()
    for index, char in enumerate(source_text):
        if char.isalpha():
            return f"{source_text[:index]}{char.lower()}{source_text[index + 1:]}"
    return source_text


def generate_example_preview(
    runtime: WordbankRuntime | None,
    *,
    stored_lemma: str,
    meaning_id: int,
    tense_label: str | None = None,
    existing_examples: list[str] | None = None,
) -> GenerateExamplePreviewResponse:
    if runtime is None:
        raise RuntimeError("Gemini example generation is unavailable.")
    normalized_lemma = normalize_token(stored_lemma)
    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    meaning = runtime.repository.get_lexeme_meaning(meaning_id)
    if lexeme is None or meaning is None:
        raise ValueError("target word meaning was not found")
    meaning_ids = {item.id for item in runtime.repository.list_lexeme_meanings(lexeme.id)}
    if meaning.id not in meaning_ids:
        raise ValueError("target word meaning was not found")
    generator = getattr(runtime.translation, "generate_example_sentence", None)
    if not callable(generator):
        raise RuntimeError("Gemini example generation is unavailable.")

    surface_forms = [
        form.form
        for form in runtime.repository.list_surface_forms(lexeme.id)
        if form.meaning_id in {None, meaning_id}
    ]
    gloss_translation = meaning_gloss_translation(
        runtime,
        lexeme_lemma=lexeme.lemma,
        lexeme_pos_tag=lexeme.pos_tag,
        meaning_gloss=meaning.gloss,
        meaning_translation=meaning.english_translation,
        meaning_pos_tag=meaning.pos_tag,
        cor_lemma_idx=meaning.cor_lemma_idx,
        cache={},
    )
    result = generator(
        ExampleSentenceGenerationInput(
            stored_lemma=lexeme.lemma,
            meaning_id=meaning.id,
            meaning_key=meaning.meaning_key,
            gloss=meaning.gloss,
            gloss_translation=gloss_translation,
            english_translation=meaning.english_translation,
            additional_translations=[
                item.english_translation
                for item in runtime.repository.list_additional_translations(
                    lexeme_id=lexeme.id,
                    meaning_id=meaning.id,
                )
            ],
            pos_tag=meaning.pos_tag,
            morphology=meaning.morphology,
            cor_lemma_idx=meaning.cor_lemma_idx,
            surface_forms=surface_forms,
            tense_label=tense_label,
            existing_examples=existing_examples or [],
        )
    )
    if result is None:
        raise RuntimeError("Gemini could not generate an example.")
    source_text = _normalize_generated_source_text(result.source_text)
    english_translation = normalize_sentence_text(result.english_translation)
    if not source_text or not english_translation:
        raise RuntimeError("Gemini generated an invalid example.")
    return GenerateExamplePreviewResponse(
        source_text=source_text,
        english_translation=english_translation,
    )


def generate_static_example_preview(
    runtime: WordbankRuntime | None,
    *,
    stored_lemma: str,
) -> GenerateExamplePreviewResponse:
    hv_word = static_hv_word_for_token(stored_lemma)
    if hv_word is None:
        raise ValueError("static word was not found")
    generator = getattr(runtime.translation, "generate_example_sentence", None) if runtime is not None else None
    if callable(generator):
        result = generator(
            ExampleSentenceGenerationInput(
                stored_lemma=hv_word.lemma,
                meaning_id=0,
                meaning_key=f"static-hv-{hv_word.lemma}",
                gloss=hv_word.english_translation,
                gloss_translation=hv_word.english_translation,
                english_translation=hv_word.english_translation,
                pos_tag=hv_word.pos_tag,
                morphology=hv_word.morphology,
                surface_forms=[hv_word.lemma],
            )
        )
        if result is not None:
            source_text = _normalize_generated_source_text(result.source_text)
            english_translation = normalize_sentence_text(result.english_translation)
            if source_text and english_translation:
                return GenerateExamplePreviewResponse(
                    source_text=source_text,
                    english_translation=english_translation,
                )
    return GenerateExamplePreviewResponse(
        source_text=hv_word.example_source,
        english_translation=hv_word.example_translation,
    )

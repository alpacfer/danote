from __future__ import annotations

from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def contextual_static_pronoun_translation(
    runtime: WordbankRuntime,
    *,
    normalized_surface: str,
    pronoun_translation: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str | None,
) -> str:
    if normalized_surface == "der" and is_existential_der_context(sentence_context):
        return "there"
    if normalized_surface not in {"der", "den", "det", "de"} or not sentence_context:
        return pronoun_translation
    contextual = runtime.translation.lookup_contextual_word_translation(
        surface_form=normalized_surface,
        lemma=normalized_surface,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=None,
        sentence_context=sentence_context,
    )
    return contextual.translation or pronoun_translation


def apply_contextual_translation_to_saved_word(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    meaning_id: int | None,
    normalized_surface: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str | None,
) -> None:
    if not sentence_context:
        return
    lexeme = runtime.repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return
    meaning = runtime.repository.get_lexeme_meaning(meaning_id) if meaning_id is not None else None
    current_translation = meaning.english_translation if meaning is not None else lexeme.english_translation
    if stored_lemma == "der" and is_existential_der_context(sentence_context):
        if current_translation == "there":
            return
        runtime.repository.replace_lexeme_translation(
            lexeme_id=lexeme.id,
            english_translation="there",
            provider="sentence_context",
        )
        return
    contextual = runtime.translation.lookup_contextual_word_translation(
        surface_form=normalized_surface,
        lemma=stored_lemma,
        pos_tag=pos_tag or (meaning.pos_tag if meaning is not None else lexeme.pos_tag),
        morphology=morphology or (meaning.morphology if meaning is not None else lexeme.morphology),
        gloss=meaning.gloss if meaning is not None else None,
        sentence_context=sentence_context,
    )
    if not contextual.translation or contextual.translation == current_translation:
        return
    if meaning is not None:
        runtime.repository.replace_lexeme_meaning_translation(
            meaning_id=meaning.id,
            english_translation=contextual.translation,
        )
        return
    runtime.repository.replace_lexeme_translation(
        lexeme_id=lexeme.id,
        english_translation=contextual.translation,
        provider=contextual.provider or "sentence_context",
    )


def is_existential_der_context(sentence_context: str | None) -> bool:
    normalized = f" {normalize_token(sentence_context or '')} "
    return " der er " in normalized or " der var " in normalized or " der findes " in normalized

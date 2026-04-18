from __future__ import annotations

from typing import TYPE_CHECKING

from app.db.repositories.sentencebank import SentenceTokenWriteRecord
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.gloss_translations import meaning_gloss_translation
from app.services.use_cases.wordbank.pronunciation_queue import queue_pronunciation_generation
from app.services.use_cases.wordbank.related_words_queue import queue_related_words_resolution
from app.services.use_cases.wordbank.runtime import WordbankRuntime
from app.services.use_cases.wordbank.verification_targets import (
    discover_word_page_verification_targets,
    queue_verification_targets,
)
from app.services.verification import WordVerificationInput

if TYPE_CHECKING:
    from app.services.use_cases.sentencebank_token_resolution import SentenceMeaningCandidate
    from app.services.use_cases.wordbank import WordbankUseCase

from app.services.gemini_translation import NonCORWordGenerationResult
from app.services.use_cases.wordbank.non_cor_generation import build_non_cor_search_seed


def persist_candidate_to_wordbank(
    wordbank_use_case: "WordbankUseCase | None",
    *,
    normalized_surface: str,
    candidate: "SentenceMeaningCandidate",
) -> object | None:
    if wordbank_use_case is None:
        return None
    try:
        return wordbank_use_case.add_word(
            normalized_surface,
            candidate.lemma,
            queue_verification=False,
            search_seed={
                "lemma": candidate.lemma,
                "surface": normalized_surface,
                "cor_id": candidate.cor_id,
                "cor_lemma_idx": candidate.cor_lemma_idx,
                "meaning_key": candidate.meaning_key,
                "gloss": candidate.gloss,
                "english_translation": candidate.english_translation,
                "pos_tag": candidate.pos_tag,
                "morphology": candidate.morphology,
            },
        )
    except Exception:
        return None


def persist_generated_to_wordbank(
    wordbank_use_case: "WordbankUseCase | None",
    *,
    normalized_surface: str,
    generated: NonCORWordGenerationResult,
) -> object | None:
    if wordbank_use_case is None:
        return None
    try:
        return wordbank_use_case.add_word(
            normalized_surface,
            generated.lemma,
            queue_verification=False,
            search_seed=build_non_cor_search_seed(
                surface_form=normalized_surface,
                generated=generated,
            ),
        )
    except Exception:
        return None


def existing_saved_token(
    runtime: WordbankRuntime,
    *,
    display_surface: str,
    normalized_surface: str,
    lemma_candidate: str,
    token_index: int,
) -> SentenceTokenWriteRecord | None:
    saved_variation = runtime.repository.find_saved_variation_translation_target(normalized_surface)
    if saved_variation is not None:
        return sentence_token_from_saved_word(
            runtime,
            token_index=token_index,
            display_surface=display_surface,
            normalized_surface=normalized_surface,
            stored_lemma=saved_variation.lemma,
            meaning_id=saved_variation.meaning_id,
        )
    if normalized_surface == lemma_candidate:
        saved_lemma = runtime.repository.find_saved_lemma_translation_target(lemma_candidate)
        if saved_lemma is not None:
            return sentence_token_from_saved_word(
                runtime,
                token_index=token_index,
                display_surface=display_surface,
                normalized_surface=normalized_surface,
                stored_lemma=saved_lemma.lemma,
                meaning_id=saved_lemma.meaning_id,
            )
    return None


def sentence_token_from_saved_word(
    runtime: WordbankRuntime,
    *,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    stored_lemma: str,
    meaning_id: int | None,
) -> SentenceTokenWriteRecord | None:
    lexeme = runtime.repository.get_lexeme(stored_lemma)
    if lexeme is None:
        return None
    meaning = runtime.repository.get_lexeme_meaning(meaning_id) if meaning_id is not None else None
    surface_row = matching_surface_form_row(
        runtime,
        lexeme_id=lexeme.id,
        normalized_surface=normalized_surface,
        meaning_id=meaning_id,
    )
    gloss_translation_cache: dict[
        tuple[str, str, str | None, str | None, str, str | None, str | None],
        str | None,
    ] = {}
    return SentenceTokenWriteRecord(
        token_index=token_index,
        surface_form=display_surface,
        normalized_surface=normalized_surface,
        stored_lemma=stored_lemma,
        lexeme_id=lexeme.id,
        meaning_id=meaning.id if meaning is not None else None,
        cor_id=surface_row.cor_id if surface_row is not None else None,
        pos_tag=(
            (surface_row.pos_tag if surface_row is not None else None)
            or (meaning.pos_tag if meaning is not None else None)
            or lexeme.pos_tag
        ),
        morphology=(
            (surface_row.morphology if surface_row is not None else None)
            or (meaning.morphology if meaning is not None else None)
            or lexeme.morphology
        ),
        gloss=meaning.gloss if meaning is not None else None,
        english_translation=(
            meaning.english_translation if meaning is not None else lexeme.english_translation
        ),
        gloss_translation=(
            meaning_gloss_translation(
                runtime,
                lexeme_lemma=lexeme.lemma,
                lexeme_pos_tag=lexeme.pos_tag,
                meaning_gloss=meaning.gloss,
                meaning_translation=meaning.english_translation,
                meaning_pos_tag=meaning.pos_tag,
                cor_lemma_idx=meaning.cor_lemma_idx,
                cache=gloss_translation_cache,
            )
            if meaning is not None
            else None
        ),
    )


def save_root_level_sentence_token(
    runtime: WordbankRuntime,
    *,
    token_index: int,
    display_surface: str,
    normalized_surface: str,
    lemma: str,
    pos_tag: str | None,
    morphology: str | None,
    cor_id: str | None,
    gloss: str | None,
    english_translation: str | None,
    gloss_translation: str | None,
    queue_verification: bool = True,
) -> SentenceTokenWriteRecord:
    lexeme_id, _inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=lemma,
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
        source="search",
    )
    surface_form, _inserted_surface_form = runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=None,
        form=normalized_surface,
        pos_tag=pos_tag,
        morphology=morphology,
        source="search",
    )
    if cor_id:
        runtime.repository.insert_surface_form_cor_variant(
            surface_form_id=surface_form.id,
            cor_id=cor_id,
        )
    runtime.nlp.add_user_lexeme(lemma)
    runtime.nlp.invalidate_pos_cache(lemma, normalized_surface)
    if queue_verification:
        queue_verification_targets(
            runtime,
            stored_lemma=lemma,
            targets=discover_word_page_verification_targets(runtime, stored_lemma=lemma),
        )
    queue_pronunciation_generation(
        runtime,
        stored_lemma=lemma,
        requested_forms=(normalized_surface,),
    )
    queue_related_words_resolution(runtime, stored_lemma=lemma)
    return SentenceTokenWriteRecord(
        token_index=token_index,
        surface_form=display_surface,
        normalized_surface=normalized_surface,
        stored_lemma=lemma,
        lexeme_id=lexeme_id,
        meaning_id=None,
        cor_id=cor_id,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=gloss,
        english_translation=english_translation,
        gloss_translation=gloss_translation,
    )


def batch_verify_new_sentence_tokens(
    runtime: WordbankRuntime,
    *,
    new_token_metadata: list[dict[str, object]],
    sentence_context: str,
) -> None:
    verification_pairs = [
        (meta, build_verification_input(runtime, meta)) for meta in new_token_metadata
    ]
    fallback_metadata = [
        meta for meta, verification_input in verification_pairs if verification_input is None
    ]
    valid_pairs = [
        (meta, verification_input)
        for meta, verification_input in verification_pairs
        if verification_input is not None
    ]
    valid_inputs = [verification_input for _meta, verification_input in valid_pairs]
    if fallback_metadata:
        queue_sentence_token_verification_fallback(runtime, fallback_metadata)
    if not valid_inputs:
        return
    try:
        results = runtime.verification.verify_word_entries_batch(
            valid_inputs,
            sentence_context=sentence_context,
        )
        error_metadata = [
            meta
            for (meta, _verification_input), result in zip(valid_pairs, results, strict=False)
            if result.status == "error"
        ]
        if error_metadata:
            queue_sentence_token_verification_fallback(runtime, error_metadata)
    except Exception:
        queue_sentence_token_verification_fallback(runtime, new_token_metadata)


def queue_sentence_token_verification_fallback(
    runtime: WordbankRuntime,
    metadata_items: list[dict[str, object]],
) -> None:
    queued_lemmas: set[str] = set()
    for meta in metadata_items:
        stored_lemma = normalize_token(str(meta.get("stored_lemma", "")))
        if not stored_lemma or stored_lemma in queued_lemmas:
            continue
        queued_lemmas.add(stored_lemma)
        queue_verification_targets(
            runtime,
            stored_lemma=stored_lemma,
            targets=discover_word_page_verification_targets(runtime, stored_lemma=stored_lemma),
        )


def build_verification_input(
    runtime: WordbankRuntime,
    meta: dict[str, object],
) -> WordVerificationInput | None:
    from app.services.use_cases.wordbank.verification_input_builder import build_verification_input

    stored_lemma = str(meta.get("stored_lemma", ""))
    stored_surface_form = meta.get("stored_surface_form")
    meaning_id = meta.get("meaning_id")
    if not stored_lemma:
        return None
    normalized_surface_form = str(stored_surface_form) if stored_surface_form else None
    if normalized_surface_form == stored_lemma:
        normalized_surface_form = None
    return build_verification_input(
        db_path=runtime.verification._db_path,
        nlp=runtime.nlp,
        cor=runtime.cor,
        stored_lemma=stored_lemma,
        stored_surface_form=normalized_surface_form,
        meaning_id=int(meaning_id) if isinstance(meaning_id, int) and meaning_id else None,
    )


def verification_metadata_for_new_sentence_token(
    token: SentenceTokenWriteRecord,
) -> list[dict[str, object]]:
    root_target = {
        "stored_lemma": token.stored_lemma,
        "stored_surface_form": None,
        "meaning_id": token.meaning_id,
    }
    if token.normalized_surface == token.stored_lemma:
        return [root_target]
    return [
        root_target,
        {
            "stored_lemma": token.stored_lemma,
            "stored_surface_form": token.normalized_surface,
            "meaning_id": token.meaning_id,
        },
    ]


def matching_surface_form_row(
    runtime: WordbankRuntime,
    *,
    lexeme_id: int,
    normalized_surface: str,
    meaning_id: int | None,
):
    rows = runtime.repository.find_surface_forms(lexeme_id=lexeme_id, form=normalized_surface)
    if not rows:
        return None
    if meaning_id is not None:
        scoped = next((row for row in rows if row.meaning_id == meaning_id), None)
        if scoped is not None:
            return scoped
    return rows[0]

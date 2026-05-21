from __future__ import annotations

from app.api.schemas.v1.wordbank import CORSearchFormResponse, CORSearchGroup, CORSearchVariant
from app.services.gemini_translation import NonCORWordGenerationInput, NonCORWordGenerationResult
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator


def generated_non_cor_response(
    translation: TranslationCollaborator,
    normalized_form: str,
) -> CORSearchFormResponse | None:
    results = translation.generate_non_cor_word_entries_batch(
        [
            NonCORWordGenerationInput(
                surface_form=normalized_form,
                lemma_candidate=normalized_form,
                pos_tag=None,
                morphology=None,
                sentence_context=None,
            )
        ]
    )
    generated = results[0] if results else None
    if generated is None or not generated.english_translation:
        return None
    lemma = normalize_token(generated.lemma)
    if not lemma:
        return None
    variant = _generated_non_cor_variant(
        normalized_form=normalized_form,
        generated=generated,
        lemma=lemma,
    )
    return CORSearchFormResponse(
        form=normalized_form,
        groups=[
            CORSearchGroup(
                lemma=lemma,
                gloss=generated.gloss,
                pos_tag=variant.pos_tag,
                variants=[variant],
            )
        ],
        did_you_mean=None,
    )


def _generated_non_cor_variant(
    *,
    normalized_form: str,
    generated: NonCORWordGenerationResult,
    lemma: str,
) -> CORSearchVariant:
    pos_tag = generated.surface_pos_tag or generated.pos_tag
    morphology = generated.surface_morphology or generated.morphology
    return CORSearchVariant(
        cor_id=f"GENERATED.NON_COR.{lemma.upper()}",
        form=normalized_form,
        lemma=lemma,
        dictionary_status="generated_non_cor",
        gloss=generated.gloss,
        gloss_translation=generated.gloss,
        gram_raw=_generated_non_cor_gram_raw(pos_tag, morphology),
        norm="N",
        lemma_idx=0,
        gram_code=0,
        variation=0,
        pos_tag=pos_tag,
        morphology=morphology,
        features={},
        extra_tags=["not in COR"],
        lemma_translation=generated.english_translation,
        saveable_translation=generated.english_translation,
        lemma_translation_provider="gemini_word_translation",
        lemma_translation_status="gemini",
        lemma_translation_reason="generated_non_cor",
    )


def _generated_non_cor_gram_raw(pos_tag: str | None, morphology: str | None) -> str:
    pos = (pos_tag or "X").strip().lower()
    morph = (morphology or "").strip()
    return f"{pos}.{morph}" if morph else pos

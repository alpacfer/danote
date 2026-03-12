from __future__ import annotations

from collections.abc import Callable

from app.services.cor_local import CORLocalEntry
from app.services.gemini_translation import ContextualWordTranslationInput
from app.services.token_classifier import normalize_token


def build_contextual_input(
    *,
    surface_form: str,
    lemma: str,
    pos_tag: str | None,
    morphology: str | None,
    gloss: str | None,
    lemma_translation_hint: str | None,
    gloss_translation_hint: str | None,
    best_cor_local_entry_with_gloss: Callable[..., CORLocalEntry | None],
) -> ContextualWordTranslationInput:
    normalized_surface = normalize_token(surface_form)
    normalized_lemma = normalize_token(lemma) or normalized_surface
    normalized_gloss = normalize_token(gloss or "") or None
    if normalized_gloss:
        return ContextualWordTranslationInput(
            surface_form=normalized_surface,
            lemma=normalized_lemma,
            pos_tag=pos_tag,
            morphology=morphology,
            gloss=normalized_gloss,
            lemma_translation_hint=lemma_translation_hint,
            gloss_translation_hint=gloss_translation_hint,
        )

    cor_entry = best_cor_local_entry_with_gloss(
        form=normalized_surface,
        lemma=normalized_lemma,
        preferred_pos_tag=pos_tag,
    )
    if cor_entry is not None:
        return ContextualWordTranslationInput(
            surface_form=normalized_surface,
            lemma=normalized_lemma,
            pos_tag=pos_tag or cor_entry.pos_tag,
            morphology=morphology or cor_entry.morphology,
            gloss=normalize_token(cor_entry.gloss or "") or None,
            lemma_translation_hint=lemma_translation_hint,
            gloss_translation_hint=gloss_translation_hint,
        )
    return ContextualWordTranslationInput(
        surface_form=normalized_surface,
        lemma=normalized_lemma,
        pos_tag=pos_tag,
        morphology=morphology,
        gloss=None,
        lemma_translation_hint=lemma_translation_hint,
        gloss_translation_hint=gloss_translation_hint,
    )

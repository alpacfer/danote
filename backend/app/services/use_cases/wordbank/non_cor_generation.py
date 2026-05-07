from __future__ import annotations

from app.services.gemini_translation import NonCORWordGenerationResult
from app.services.token_classifier import normalize_token


def build_non_cor_search_seed(
    *,
    surface_form: str,
    generated: NonCORWordGenerationResult,
    target_meaning_id: int | None = None,
) -> dict[str, object]:
    normalized_surface = normalize_token(surface_form)
    if not normalized_surface:
        raise ValueError("surface_form is required")
    return {
        "lemma": generated.lemma,
        "surface": normalized_surface,
        "dictionary_status": "generated_non_cor",
        "cor_id": None,
        "cor_lemma_idx": None,
        "meaning_key": normalize_token(generated.meaning_key or "") or generated.lemma,
        "gloss": None,
        "english_translation": generated.english_translation,
        "pos_tag": generated.surface_pos_tag or generated.pos_tag,
        "morphology": generated.surface_morphology or generated.morphology,
        "target_meaning_id": target_meaning_id,
    }

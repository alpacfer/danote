from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class AddWordInputs:
    normalized_surface: str
    stored_lemma: str
    normalized_cor_id: str | None
    selected_pos_tag: str | None
    selected_morphology: str | None


def normalize_add_word_inputs(
    surface_token: str,
    lemma_candidate: str | None,
    cor_id: str | None,
    pos_tag: str | None,
    morphology: str | None,
) -> AddWordInputs:
    normalized_surface = normalize_token(surface_token)
    normalized_lemma = normalize_token(lemma_candidate or "")
    if not normalized_surface and not normalized_lemma:
        raise ValueError("surface_token or lemma_candidate is required")
    return AddWordInputs(
        normalized_surface=normalized_surface,
        stored_lemma=normalized_lemma or normalized_surface,
        normalized_cor_id=normalize_token(cor_id or "") or None,
        selected_pos_tag=normalize_token(pos_tag or "") or None,
        selected_morphology=normalize_token(morphology or "") or None,
    )

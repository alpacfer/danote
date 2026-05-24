from __future__ import annotations

from app.services.use_cases.wordbank.runtime import WordbankRuntime


def canonicalise_lemma_candidate(
    runtime: WordbankRuntime,
    *,
    surface_token: str,
    lemma_candidate: str | None,
    cor_id: str | None,
    pos_tag: str | None,
) -> str | None:
    """If no lemma was supplied, derive the canonical COR lemma from the surface form.

    Stops misfiled inflection lemmas like 'går' from becoming their own root
    when the canonical lemma 'gå' exists. Only fires when the surface form
    resolves unambiguously to a single COR lemma; otherwise we leave the
    caller-provided value alone so downstream POS-aware resolution can choose.
    """
    if lemma_candidate is not None and lemma_candidate.strip():
        return lemma_candidate
    if cor_id:
        return lemma_candidate
    normalized_surface = surface_token.strip()
    if not normalized_surface:
        return lemma_candidate
    entries = runtime.cor.cor_local_entries_for_form(
        form=normalized_surface,
        lemma=normalized_surface,
        preferred_pos_tag=pos_tag,
    )
    if not entries:
        return lemma_candidate
    canonical_lemmas = {entry.lemma for entry in entries if entry.lemma}
    if len(canonical_lemmas) != 1:
        return lemma_candidate
    canonical = next(iter(canonical_lemmas))
    if canonical == normalized_surface:
        return lemma_candidate
    return canonical

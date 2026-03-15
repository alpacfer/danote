from __future__ import annotations

from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    CORSearchGroup,
    CORSearchVariant,
)
from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    AzureFrameCacheKey,
    ContextualCacheKey,
    lemma_translation_for_entry,
    lookup_translation_for_cor_gloss,
    lookup_translation_for_cor_local_entry,
    prime_cor_form_contextual_translations,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator


def search_cor_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    translation: TranslationCollaborator,
    form: str,
    *,
    limit: int = 100,
    include_translations: bool = True,
) -> CORSearchFormResponse:
    normalized_form = normalize_token(form)
    if not normalized_form:
        raise ValueError("form is required")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if cor_local_lexicon_service is None:
        raise RuntimeError("COR local lookup service is unavailable.")

    try:
        entries = cor_local_lexicon_service.lookup_form(normalized_form, limit=limit)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "COR local database is unavailable. Build backend/resources/dictionaries/cor.sqlite first."
        ) from exc
    entries = [entry for entry in entries if entry.norm == "N"]
    entries = consolidate_cor_local_entries(entries)
    entries = drop_glossless_when_gloss_exists(entries)

    groups: list[CORSearchGroup] = []
    contextual_translation_cache: dict[ContextualCacheKey, str | None] = {}
    lemma_translation_cache: dict[AzureFrameCacheKey, str | None] = {}
    gloss_translation_cache: dict[str, str | None] = {}
    if include_translations:
        prime_cor_form_contextual_translations(
            translation,
            entries,
            cache=contextual_translation_cache,
            lemma_cache=lemma_translation_cache,
            gloss_cache=gloss_translation_cache,
        )
    grouped: dict[tuple[str, str | None, str | None], int] = {}
    for entry in entries:
        key = (entry.lemma, entry.gloss, entry.pos_tag)
        group_index = grouped.get(key)
        if include_translations:
            lemma_translation = lookup_translation_for_cor_local_entry(
                translation,
                entry,
                lemma_translation_cache,
                contextual_translation_cache,
                gloss_cache=gloss_translation_cache,
                strict_azure=True,
            )
            gloss_translation = lookup_translation_for_cor_gloss(
                translation,
                entry=entry,
                lemma_translation=lemma_translation,
                cache=contextual_translation_cache,
                strict_azure=True,
                gloss_cache=gloss_translation_cache,
            )
        else:
            lemma_translation = None
            gloss_translation = None
        if group_index is None:
            groups.append(
                CORSearchGroup(
                    lemma=entry.lemma,
                    gloss=entry.gloss,
                    pos_tag=entry.pos_tag,
                    variants=[
                        cor_local_variant(
                            entry,
                            lemma_translation=lemma_translation,
                            gloss_translation=gloss_translation,
                        )
                    ],
                )
            )
            grouped[key] = len(groups) - 1
            continue
        groups[group_index].variants.append(
            cor_local_variant(
                entry,
                lemma_translation=lemma_translation,
                gloss_translation=gloss_translation,
            )
        )

    return CORSearchFormResponse(form=normalized_form, groups=groups)


def search_cor_lemma_paradigm(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    translation: TranslationCollaborator,
    lemma_idx: int,
    *,
    limit: int = 1000,
) -> CORLemmaParadigmResponse:
    if lemma_idx < 1:
        raise ValueError("lemma_idx must be >= 1")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    if cor_local_lexicon_service is None:
        raise RuntimeError("COR local lookup service is unavailable.")

    try:
        entries = cor_local_lexicon_service.lookup_lemma(lemma_idx, limit=limit)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "COR local database is unavailable. Build backend/resources/dictionaries/cor.sqlite first."
        ) from exc
    entries = [entry for entry in entries if entry.norm == "N"]
    entries = consolidate_cor_local_entries(entries)
    entries = drop_glossless_when_gloss_exists(entries)

    contextual_translation_cache: dict[ContextualCacheKey, str | None] = {}
    lemma_translation_cache: dict[AzureFrameCacheKey, str | None] = {}
    return CORLemmaParadigmResponse(
        lemma_idx=lemma_idx,
        variants=[
            cor_local_variant(
                entry,
                lemma_translation=lemma_translation_for_entry(
                    translation,
                    entry,
                    lemma_translation_cache,
                    contextual_translation_cache,
                ),
                gloss_translation=lookup_translation_for_cor_gloss(
                    translation,
                    entry=entry,
                    lemma_translation=lemma_translation_for_entry(
                        translation,
                        entry,
                        lemma_translation_cache,
                        contextual_translation_cache,
                    ),
                    cache=contextual_translation_cache,
                ),
            )
            for entry in entries
        ],
    )


def best_cor_local_entry_for_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    form: str,
    lemma: str,
    preferred_pos_tag: str | None,
    preferred_lemma_idx: int | None = None,
) -> CORLocalEntry | None:
    entries = cor_local_entries_for_form(
        cor_local_lexicon_service,
        form=form,
        lemma=lemma,
        preferred_pos_tag=preferred_pos_tag,
        preferred_lemma_idx=preferred_lemma_idx,
    )
    if not entries:
        return None
    return entries[0]


def cor_local_entries_for_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    form: str,
    lemma: str,
    preferred_pos_tag: str | None,
    preferred_lemma_idx: int | None = None,
) -> list[CORLocalEntry]:
    if cor_local_lexicon_service is None:
        return []
    normalized_form = normalize_token(form)
    normalized_lemma = normalize_token(lemma)
    if not normalized_form or not normalized_lemma:
        return []
    try:
        entries = cor_local_lexicon_service.lookup_form(normalized_form, limit=500)
    except FileNotFoundError:
        return []
    if not entries:
        return []
    filtered = [
        entry
        for entry in entries
        if normalize_token(entry.lemma) == normalized_lemma and entry.norm == "N"
    ]
    if preferred_lemma_idx is not None:
        preferred_idx_entries = [entry for entry in filtered if entry.lemma_idx == preferred_lemma_idx]
        if preferred_idx_entries:
            filtered = preferred_idx_entries
    if not filtered:
        return []
    if preferred_pos_tag:
        preferred = [entry for entry in filtered if entry.pos_tag == preferred_pos_tag]
        if preferred:
            filtered = preferred
    filtered = consolidate_cor_local_entries(filtered)
    filtered = drop_glossless_when_gloss_exists(filtered)
    return filtered


def best_cor_local_lemma_entry(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    lemma_idx: int,
    lemma: str,
    preferred_pos_tag: str | None,
    allow_lemma_mismatch: bool = False,
) -> CORLocalEntry | None:
    if cor_local_lexicon_service is None or lemma_idx < 1:
        return None
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        return None
    try:
        entries = cor_local_lexicon_service.lookup_lemma(lemma_idx, limit=1000)
    except FileNotFoundError:
        return None
    filtered = [entry for entry in entries if entry.norm == "N"]
    matching_lemma_entries = [
        entry for entry in filtered if normalize_token(entry.lemma) == normalized_lemma
    ]
    if matching_lemma_entries:
        filtered = matching_lemma_entries
    elif not allow_lemma_mismatch:
        return None
    if preferred_pos_tag:
        preferred = [entry for entry in filtered if entry.pos_tag == preferred_pos_tag]
        if preferred:
            filtered = preferred
    filtered = consolidate_cor_local_entries(filtered)
    filtered = drop_glossless_when_gloss_exists(filtered)
    exact_lemma_form = [entry for entry in filtered if normalize_token(entry.form) == normalized_lemma]
    if exact_lemma_form:
        return exact_lemma_form[0]
    if allow_lemma_mismatch:
        exact_canonical_form = [
            entry for entry in filtered if normalize_token(entry.form) == normalize_token(entry.lemma)
        ]
        if exact_canonical_form:
            return exact_canonical_form[0]
    return filtered[0] if filtered else None


def cor_local_entries_for_lemma_idx(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    lemma_idx: int,
    lemma: str,
    preferred_pos_tag: str | None,
) -> list[CORLocalEntry]:
    if cor_local_lexicon_service is None or lemma_idx < 1:
        return []
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        return []
    try:
        entries = cor_local_lexicon_service.lookup_lemma(lemma_idx, limit=1000)
    except FileNotFoundError:
        return []
    filtered = [
        entry
        for entry in entries
        if entry.norm == "N" and normalize_token(entry.lemma) == normalized_lemma
    ]
    if preferred_pos_tag:
        preferred = [entry for entry in filtered if entry.pos_tag == preferred_pos_tag]
        if preferred:
            filtered = preferred
    filtered = consolidate_cor_local_entries(filtered)
    return drop_glossless_when_gloss_exists(filtered)


def cor_local_entry_for_cor_id(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    cor_id: str,
) -> CORLocalEntry | None:
    if cor_local_lexicon_service is None:
        return None
    normalized_cor_id = " ".join(cor_id.strip().split())
    if not normalized_cor_id:
        return None
    try:
        entry = cor_local_lexicon_service.lookup_cor_id(normalized_cor_id)
    except FileNotFoundError:
        return None
    if entry is None or entry.norm != "N":
        return None
    return entry


def consolidate_cor_local_entries(entries: list[CORLocalEntry]) -> list[CORLocalEntry]:
    if len(entries) < 2:
        return entries

    consolidated: dict[tuple[str, str, str | None, str | None, str | None], CORLocalEntry] = {}
    order: list[tuple[str, str, str | None, str | None, str | None]] = []
    for entry in entries:
        key = (entry.form, entry.lemma, entry.gloss, entry.pos_tag, entry.norm)
        existing = consolidated.get(key)
        if existing is None:
            consolidated[key] = entry
            order.append(key)
            continue

        grams: list[str] = []
        for source in (existing.gram_raw, entry.gram_raw):
            for gram in [part.strip() for part in source.split("|")]:
                if gram and gram not in grams:
                    grams.append(gram)
        merged_gram = " | ".join(grams)

        merged_features = dict(existing.features)
        for feature_key, feature_value in entry.features.items():
            current = merged_features.get(feature_key)
            if current is None:
                merged_features[feature_key] = feature_value
            elif current != feature_value:
                merged_features.pop(feature_key, None)

        merged_extra_tags = [*existing.extra_tags]
        for tag in entry.extra_tags:
            if tag not in merged_extra_tags:
                merged_extra_tags.append(tag)

        consolidated[key] = CORLocalEntry(
            cor_id=existing.cor_id,
            lemma=existing.lemma,
            gloss=existing.gloss,
            gram_raw=merged_gram,
            form=existing.form,
            norm=existing.norm,
            lemma_idx=existing.lemma_idx,
            gram_code=existing.gram_code,
            variation=existing.variation,
            pos_tag=existing.pos_tag,
            morphology=existing.morphology,
            features=merged_features,
            extra_tags=merged_extra_tags,
        )

    return [consolidated[item] for item in order]


def drop_glossless_when_gloss_exists(entries: list[CORLocalEntry]) -> list[CORLocalEntry]:
    if len(entries) < 2:
        return entries

    has_gloss_by_form_pos: dict[tuple[str, str | None], bool] = {}
    for entry in entries:
        key = (entry.form, entry.pos_tag)
        if entry.gloss and entry.gloss.strip():
            has_gloss_by_form_pos[key] = True
        else:
            has_gloss_by_form_pos.setdefault(key, False)

    filtered: list[CORLocalEntry] = []
    for entry in entries:
        key = (entry.form, entry.pos_tag)
        if has_gloss_by_form_pos.get(key, False):
            if entry.gloss and entry.gloss.strip():
                filtered.append(entry)
            continue
        filtered.append(entry)
    return filtered


def cor_local_variant(
    entry: CORLocalEntry,
    *,
    lemma_translation: str | None = None,
    gloss_translation: str | None = None,
) -> CORSearchVariant:
    return CORSearchVariant(
        cor_id=entry.cor_id,
        form=entry.form,
        lemma=entry.lemma,
        gloss=entry.gloss,
        gloss_translation=gloss_translation,
        gram_raw=entry.gram_raw,
        norm=entry.norm,
        lemma_idx=entry.lemma_idx,
        gram_code=entry.gram_code,
        variation=entry.variation,
        pos_tag=entry.pos_tag,
        morphology=entry.morphology,
        features=entry.features,
        extra_tags=entry.extra_tags,
        lemma_translation=lemma_translation,
    )

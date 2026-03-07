from __future__ import annotations

import re

from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    CORSearchGroup,
    CORSearchVariant,
)
from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator


def search_cor_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    translation: TranslationCollaborator,
    form: str,
    *,
    limit: int = 100,
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
    lemma_translation_cache: dict[str, str | None] = {}
    gloss_translation_cache: dict[str, str | None] = {}
    grouped: dict[tuple[str, str | None, str | None], int] = {}
    for entry in entries:
        key = (entry.lemma, entry.gloss, entry.pos_tag)
        group_index = grouped.get(key)
        lemma_translation = lookup_translation_for_cor_local_entry(
            translation,
            entry,
            lemma_translation_cache,
        )
        gloss_translation = lookup_translation_for_cor_gloss(
            translation,
            entry.gloss,
            gloss_translation_cache,
        )
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

    lemma_translation_cache: dict[str, str | None] = {}
    gloss_translation_cache: dict[str, str | None] = {}
    return CORLemmaParadigmResponse(
        lemma_idx=lemma_idx,
        variants=[
            cor_local_variant(
                entry,
                lemma_translation=lookup_translation_for_cor_local_entry(
                    translation,
                    entry,
                    lemma_translation_cache,
                ),
                gloss_translation=lookup_translation_for_cor_gloss(
                    translation,
                    entry.gloss,
                    gloss_translation_cache,
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
) -> CORLocalEntry | None:
    if cor_local_lexicon_service is None:
        return None
    normalized_form = normalize_token(form)
    normalized_lemma = normalize_token(lemma)
    if not normalized_form or not normalized_lemma:
        return None
    try:
        entries = cor_local_lexicon_service.lookup_form(normalized_form, limit=500)
    except FileNotFoundError:
        return None
    if not entries:
        return None
    filtered = [
        entry
        for entry in entries
        if normalize_token(entry.lemma) == normalized_lemma and entry.norm == "N"
    ]
    if not filtered:
        return None
    if preferred_pos_tag:
        preferred = [entry for entry in filtered if entry.pos_tag == preferred_pos_tag]
        if preferred:
            filtered = preferred
    return filtered[0]


def lookup_translation_for_cor_gloss(
    translation: TranslationCollaborator,
    gloss: str | None,
    cache: dict[str, str | None] | None = None,
) -> str | None:
    if translation._translation_service is None:
        return None
    normalized_gloss = normalize_token(gloss or "")
    if not normalized_gloss:
        return None
    if cache is not None and normalized_gloss in cache:
        return cache[normalized_gloss]

    translated = translation.lookup_translation(normalized_gloss)
    if translated and translated != normalized_gloss:
        if cache is not None:
            cache[normalized_gloss] = translated
        return translated

    parts = [normalize_token(part) for part in normalized_gloss.split(",")]
    parts = [part for part in parts if part]
    if len(parts) > 1:
        translated_parts: list[str] = []
        for part in parts:
            part_translated = translation.lookup_translation(part)
            translated_parts.append(part_translated or part)
        merged = ", ".join(translated_parts)
        if cache is not None:
            cache[normalized_gloss] = merged
        return merged

    if cache is not None:
        cache[normalized_gloss] = translated
    return translated


def lookup_translation_for_cor_local_entry(
    translation: TranslationCollaborator,
    entry: CORLocalEntry,
    cache: dict[str, str | None] | None = None,
) -> str | None:
    if translation._translation_service is None:
        return None

    frame_kind, frame_text = cor_translation_frame(entry)
    if cache is not None and frame_text in cache:
        translated = cache[frame_text]
    else:
        translated = translation.lookup_translation(frame_text)
        if cache is not None:
            cache[frame_text] = translated
    if not translated:
        return None
    return strip_cor_translation_frame(frame_kind, translated)


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


def cor_translation_frame(entry: CORLocalEntry) -> tuple[str, str]:
    lemma = normalize_token(entry.lemma)
    if not lemma:
        return "raw", entry.lemma

    gram = entry.gram_raw.lower()
    pos_code = gram.split(".", 1)[0].strip()
    if pos_code == "vb":
        return "verb", f"at {lemma}"
    if pos_code == "sb":
        article = "et" if re.search(r"(^|\.)itk(\.|$)", gram) else "en"
        return "noun", f"{article} {lemma}"
    if pos_code == "adj":
        return "adjective", f"en {lemma} ting"
    if pos_code == "adv":
        return "adverb", f"han gør det {lemma}"
    if pos_code == "pron":
        return "pronoun", f"{lemma} er her"
    if pos_code == "præp":
        return "preposition", f"{lemma} huset"
    if pos_code == "konj":
        return "conjunction", f"..., {lemma} jeg går"
    if pos_code == "art":
        return "article", f"{lemma} bog"
    if pos_code == "prop":
        return "proper_noun", f"navnet {lemma}"
    if pos_code == "talord":
        return "numeral", f"{lemma} bøger"
    return "raw", lemma


def strip_cor_translation_frame(frame_kind: str, translated: str) -> str | None:
    cleaned = normalize_token(translated)
    if not cleaned:
        return None
    if frame_kind == "verb":
        return cleaned

    value = cleaned
    if frame_kind == "noun":
        value = re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "adjective":
        value = re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+things?$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "adverb":
        value = re.sub(r"^(?:he|she|it)\s+does\s+it\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "pronoun":
        value = re.sub(r"\s+is\s+here$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "preposition":
        value = re.sub(r"\s+(?:the\s+)?house$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "conjunction":
        value = re.sub(r"\s+i\s+go$", "", value, flags=re.IGNORECASE)
        value = value.strip(" ,")
    elif frame_kind == "article":
        value = re.sub(r"\s+books?$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "proper_noun":
        value = re.sub(r"^(?:the\s+)?name\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "numeral":
        value = re.sub(r"\s+books?$", "", value, flags=re.IGNORECASE)

    value = normalize_token(value)
    return value or cleaned


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

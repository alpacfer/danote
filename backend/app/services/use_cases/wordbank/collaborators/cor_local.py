from __future__ import annotations

from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    CORSearchGroup,
    CORSearchVariant,
)
from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.en_gemini_translation import ENGeminiTranslationService
from app.services.fuzzy_search import fuzzy_suggest
from app.services.token_classifier import normalize_token
from app.services.use_cases.static_presaved_words import (
    StaticPresavedWord,
    static_presaved_word_for_token,
)
from app.services.use_cases.static_pronouns import StaticPronoun, static_pronoun_for_token
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    AzureFrameCacheKey,
    ContextualCacheKey,
    lemma_translation_for_entry,
    lookup_translation_for_cor_gloss,
    prime_cor_form_contextual_translations,
    search_translation_decision_for_cor_local_entry,
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
    static_pronoun = static_pronoun_for_token(normalized_form)
    if static_pronoun is not None:
        return static_pronoun_cor_search_response(normalized_form, static_pronoun)
    static_presaved_word = static_presaved_word_for_token(normalized_form)
    if static_presaved_word is not None:
        return static_presaved_word_cor_search_response(normalized_form, static_presaved_word)
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

    did_you_mean: str | None = None
    if not entries:
        suggestions = fuzzy_suggest(normalized_form, cor_local_lexicon_service.unique_lemmas)
        if suggestions:
            did_you_mean = suggestions[0]
            try:
                fallback_entries = cor_local_lexicon_service.lookup_form(did_you_mean, limit=limit)
            except FileNotFoundError:
                fallback_entries = []
            fallback_entries = [e for e in fallback_entries if e.norm == "N"]
            fallback_entries = consolidate_cor_local_entries(fallback_entries)
            fallback_entries = drop_glossless_when_gloss_exists(fallback_entries)
            entries = fallback_entries

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
            translation_decision = search_translation_decision_for_cor_local_entry(
                translation,
                entry,
                cache=lemma_translation_cache,
                contextual_cache=contextual_translation_cache,
                gloss_cache=gloss_translation_cache,
                strict_azure=True,
            )
            gloss_translation = lookup_translation_for_cor_gloss(
                translation,
                entry=entry,
                lemma_translation=translation_decision.lemma_translation,
                cache=contextual_translation_cache,
                strict_azure=True,
                gloss_cache=gloss_translation_cache,
            )
        else:
            translation_decision = None
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
                            lemma_translation=translation_decision.lemma_translation if translation_decision else None,
                            gloss_translation=gloss_translation,
                            saveable_translation=translation_decision.saveable_translation if translation_decision else None,
                            lemma_translation_provider=translation_decision.lemma_translation_provider if translation_decision else None,
                            lemma_translation_status=translation_decision.lemma_translation_status if translation_decision else None,
                            lemma_translation_reason=translation_decision.lemma_translation_reason if translation_decision else None,
                        )
                    ],
                )
            )
            grouped[key] = len(groups) - 1
            continue
        groups[group_index].variants.append(
            cor_local_variant(
                entry,
                lemma_translation=translation_decision.lemma_translation if translation_decision else None,
                gloss_translation=gloss_translation,
                saveable_translation=translation_decision.saveable_translation if translation_decision else None,
                lemma_translation_provider=translation_decision.lemma_translation_provider if translation_decision else None,
                lemma_translation_status=translation_decision.lemma_translation_status if translation_decision else None,
                lemma_translation_reason=translation_decision.lemma_translation_reason if translation_decision else None,
            )
        )

    return CORSearchFormResponse(form=normalized_form, groups=groups, did_you_mean=did_you_mean)


def filter_cor_form_response_by_en_query(
    response: CORSearchFormResponse,
    *,
    en_query: str,
    en_gemini_translation_service: ENGeminiTranslationService | None,
) -> CORSearchFormResponse:
    """Drop COR groups whose Danish meaning Gemini judges not to translate ``en_query``.

    On any Gemini failure the response is returned unchanged.
    """
    if en_gemini_translation_service is None or not response.groups or not en_query.strip():
        return response

    choices: list[dict[str, object]] = []
    group_indices = set(range(len(response.groups)))
    for index, group in enumerate(response.groups):
        first_variant = group.variants[0] if group.variants else None
        choices.append(
            {
                "id": str(index),
                "danish_lemma": group.lemma,
                "danish_gloss": group.gloss or "",
                "english_gloss": (first_variant.gloss_translation if first_variant else None) or "",
                "lemma_translation": (first_variant.lemma_translation if first_variant else None) or "",
                "pos": group.pos_tag or "",
            }
        )

    try:
        decisions = en_gemini_translation_service.select_translation_matches(
            query=en_query.strip(),
            choices=choices,
        )
    except Exception:
        return response

    if not decisions:
        return response

    matching_indices: set[int] = set()
    for raw_id, matches in decisions.items():
        try:
            int_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if matches and int_id in group_indices:
            matching_indices.add(int_id)

    if not matching_indices:
        return response

    filtered_groups = [group for index, group in enumerate(response.groups) if index in matching_indices]
    return CORSearchFormResponse(
        form=response.form,
        groups=filtered_groups,
        did_you_mean=response.did_you_mean,
    )


def static_pronoun_cor_search_response(form: str, pronoun: StaticPronoun) -> CORSearchFormResponse:
    variant = CORSearchVariant(
        cor_id=f"STATIC.PRONOUN.{pronoun.lemma.upper()}",
        form=pronoun.lemma,
        lemma=pronoun.lemma,
        gloss=None,
        gloss_translation=None,
        gram_raw="pron",
        norm="N",
        lemma_idx=0,
        gram_code=0,
        variation=0,
        pos_tag=pronoun.pos_tag,
        morphology=pronoun.morphology,
        features={},
        extra_tags=[],
        lemma_translation=pronoun.english_translation,
        saveable_translation=pronoun.english_translation,
        lemma_translation_provider="static_pronoun",
        lemma_translation_status="provider",
        lemma_translation_reason=None,
    )
    return CORSearchFormResponse(
        form=form,
        groups=[
            CORSearchGroup(
                lemma=pronoun.lemma,
                gloss=None,
                pos_tag=pronoun.pos_tag,
                variants=[variant],
            )
        ],
        did_you_mean=None,
    )


def static_presaved_word_cor_search_response(form: str, word: StaticPresavedWord) -> CORSearchFormResponse:
    variant = CORSearchVariant(
        cor_id=f"STATIC.PRESAVED.{word.lemma.upper()}",
        form=word.lemma,
        lemma=word.lemma,
        gloss=None,
        gloss_translation=None,
        gram_raw="",
        norm="N",
        lemma_idx=0,
        gram_code=0,
        variation=0,
        pos_tag=word.pos_tag,
        morphology=word.morphology,
        features={},
        extra_tags=[],
        lemma_translation=word.english_translation,
        saveable_translation=word.english_translation,
        lemma_translation_provider="static_presaved_word",
        lemma_translation_status="provider",
        lemma_translation_reason=None,
    )
    return CORSearchFormResponse(
        form=form,
        groups=[
            CORSearchGroup(
                lemma=word.lemma,
                gloss=None,
                pos_tag=word.pos_tag,
                variants=[variant],
            )
        ],
        did_you_mean=None,
    )
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


def cor_local_entries_for_surface_form(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    form: str,
    preferred_pos_tag: str | None,
) -> list[CORLocalEntry]:
    if cor_local_lexicon_service is None:
        return []
    normalized_form = normalize_token(form)
    if not normalized_form:
        return []
    try:
        entries = cor_local_lexicon_service.lookup_form(normalized_form, limit=500)
    except FileNotFoundError:
        return []
    if not entries:
        return []
    filtered = [entry for entry in entries if entry.norm == "N"]
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


def _verb_form_class(gram_raw: str) -> str | None:
    chunks = [chunk.strip() for chunk in gram_raw.lower().split(".") if chunk.strip()]
    if len(chunks) < 2 or chunks[0] != "vb":
        return None
    head = chunks[1]
    if head == "perf":
        return "perf.part"
    if head == "præs" and len(chunks) >= 3 and chunks[2] == "part":
        return "præs.part"
    if head in {"præs", "præt", "inf"}:
        return f"{head}.fin"
    return head


def consolidate_cor_local_entries(entries: list[CORLocalEntry]) -> list[CORLocalEntry]:
    if len(entries) < 2:
        return entries

    consolidated: dict[tuple[str, str, str | None, str | None, str | None, str | None], CORLocalEntry] = {}
    order: list[tuple[str, str, str | None, str | None, str | None, str | None]] = []
    for entry in entries:
        verb_class = _verb_form_class(entry.gram_raw) if entry.pos_tag == "VERB" else None
        key = (entry.form, entry.lemma, entry.gloss, entry.pos_tag, entry.norm, verb_class)
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
    saveable_translation: str | None = None,
    lemma_translation_provider: str | None = None,
    lemma_translation_status: str | None = None,
    lemma_translation_reason: str | None = None,
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
        saveable_translation=saveable_translation,
        lemma_translation_provider=lemma_translation_provider,
        lemma_translation_status=lemma_translation_status,
        lemma_translation_reason=lemma_translation_reason,
    )

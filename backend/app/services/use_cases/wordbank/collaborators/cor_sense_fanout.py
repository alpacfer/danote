from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import (
    CORSearchFormResponse,
    CORSearchGroup,
    CORSearchVariant,
)
from app.services.gemini_sense_discovery import (
    DiscoveredSense,
    SenseDiscoveryCorCandidate,
    SenseDiscoveryInput,
    is_sense_discoverable_pos,
)
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_actions import (
    SavedMeaningMatch,
    _matching_saved_meaning_id,
    load_saved_meanings_for_lemmas,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator


def expand_cor_search_response_with_senses(
    response: CORSearchFormResponse,
    *,
    translation: TranslationCollaborator,
    db_path: Path,
    owner_user_id: int = 1,
) -> CORSearchFormResponse:
    """Expand each ``CORSearchGroup`` into one group per discovered sense.

    Polysemous lemmas (verbs like ``slå``/``holde``/``gå``, nouns and adjectives
    with multiple meanings) get one card per sense in the search dialog. The
    sense discovery is cached, so repeat searches don't pay the Gemini cost.
    """
    if not response.groups:
        return response
    saved_meanings = load_saved_meanings_for_lemmas(
        db_path,
        [group.lemma for group in response.groups],
        owner_user_id=owner_user_id,
    )
    expanded_groups: list[CORSearchGroup] = []
    for group in response.groups:
        senses = _discover_for_group(group, translation=translation)
        if not senses:
            expanded_groups.append(_attach_saved_to_group(group, saved_meanings))
            continue
        if len(senses) == 1:
            expanded_groups.append(
                _attach_saved_to_group(
                    _rewrite_group_with_sense(group, senses[0]),
                    saved_meanings,
                )
            )
            continue
        for sense in senses:
            expanded_groups.append(
                _attach_saved_to_group(
                    _rewrite_group_with_sense(group, sense),
                    saved_meanings,
                )
            )
    return CORSearchFormResponse(
        form=response.form,
        groups=expanded_groups,
        did_you_mean=response.did_you_mean,
    )


def _discover_for_group(
    group: CORSearchGroup,
    *,
    translation: TranslationCollaborator,
) -> list[DiscoveredSense]:
    if not is_sense_discoverable_pos(group.pos_tag):
        return []
    if not group.variants:
        return []
    discover = getattr(translation, "discover_senses", None)
    if not callable(discover):
        return []
    candidates: list[SenseDiscoveryCorCandidate] = []
    seen: set[tuple[int | None, str | None]] = set()
    for variant in group.variants:
        key = (variant.lemma_idx, variant.pos_tag)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            SenseDiscoveryCorCandidate(
                cor_id=variant.cor_id,
                lemma=variant.lemma,
                gloss=variant.gloss,
                pos_tag=variant.pos_tag,
                lemma_idx=variant.lemma_idx,
            )
        )
    payload = SenseDiscoveryInput(
        lemma=group.lemma,
        pos_tag=group.pos_tag,
        cor_gloss=group.gloss,
        cor_candidates=candidates,
    )
    result = discover(payload)
    if result is None:
        return []
    return list(result.senses)


def _rewrite_group_with_sense(
    group: CORSearchGroup,
    sense: DiscoveredSense,
) -> CORSearchGroup:
    primary_variant = group.variants[0]
    rewritten_variant = _rewrite_variant_with_sense(primary_variant, sense)
    extra_variants = [_rewrite_variant_with_sense(variant, sense) for variant in group.variants[1:]]
    return CORSearchGroup(
        lemma=group.lemma,
        gloss=sense.gloss,
        pos_tag=group.pos_tag,
        variants=[rewritten_variant, *extra_variants],
    )


def _rewrite_variant_with_sense(
    variant: CORSearchVariant,
    sense: DiscoveredSense,
) -> CORSearchVariant:
    return variant.model_copy(
        update={
            "meaning_key": sense.meaning_key,
            "gloss": sense.gloss,
            "english_gloss": sense.english_gloss,
            # gloss_translation is the existing field the frontend renders as
            # the parenthetical after the lemma translation. Populate it from
            # english_gloss when present so the wordbank header reads
            # 'playing card (a piece of stiff paper used in card games)'
            # without us needing to add a new render path.
            "gloss_translation": sense.english_gloss,
            "lemma_translation": sense.english_translation,
            "saveable_translation": sense.english_translation,
            "lemma_translation_provider": variant.lemma_translation_provider or "gemini",
            "lemma_translation_status": variant.lemma_translation_status or "gemini",
            "alternative_translations": list(sense.alternative_translations),
            "example_da": sense.example_da,
            "example_en": sense.example_en,
        }
    )


def _attach_saved_to_group(
    group: CORSearchGroup,
    saved_meanings: dict[str, dict[str, list[SavedMeaningMatch]]],
) -> CORSearchGroup:
    by_key = saved_meanings.get(normalize_token(group.lemma))
    if not by_key:
        return group
    updated_variants = [_attach_saved_to_variant(variant, by_key) for variant in group.variants]
    return CORSearchGroup(
        lemma=group.lemma,
        gloss=group.gloss,
        pos_tag=group.pos_tag,
        variants=updated_variants,
    )


def _attach_saved_to_variant(
    variant: CORSearchVariant,
    by_key: dict[str, list[SavedMeaningMatch]],
) -> CORSearchVariant:
    if variant.saved_meaning_id is not None:
        return variant
    saved_id: int | None = None
    if variant.meaning_key is not None:
        saved_id = _matching_saved_meaning_id(
            by_key.get(variant.meaning_key) or [],
            pos_tag=variant.pos_tag,
            cor_lemma_idx=variant.lemma_idx,
        )
    if saved_id is None and len(by_key) == 1 and variant.meaning_key is None:
        saved_id = _matching_saved_meaning_id(
            next(iter(by_key.values())),
            pos_tag=variant.pos_tag,
            cor_lemma_idx=variant.lemma_idx,
        )
    if saved_id is None:
        return variant
    return variant.model_copy(update={"saved_meaning_id": saved_id})

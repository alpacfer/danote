from __future__ import annotations

from dataclasses import dataclass

from app.services.gemini_sense_discovery import (
    DiscoveredSense,
    SenseDiscoveryCorCandidate,
    SenseDiscoveryInput,
    is_sense_discoverable_pos,
)
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.meaning_sections import (
    ensure_wordbank_meaning_compatibility,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class ExpandLemmaSensesResult:
    lemma: str
    status: str
    discovered_count: int
    inserted_count: int
    renamed_legacy: bool


def expand_lemma_senses(runtime: WordbankRuntime, *, lemma: str) -> ExpandLemmaSensesResult:
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        raise ValueError("lemma is required")
    ensure_wordbank_meaning_compatibility(runtime, lemma=normalized_lemma)

    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        return ExpandLemmaSensesResult(
            lemma=normalized_lemma,
            status="lemma_not_found",
            discovered_count=0,
            inserted_count=0,
            renamed_legacy=False,
        )

    pos_tag = lexeme.pos_tag
    if not is_sense_discoverable_pos(pos_tag):
        return ExpandLemmaSensesResult(
            lemma=normalized_lemma,
            status="pos_unsupported",
            discovered_count=0,
            inserted_count=0,
            renamed_legacy=False,
        )

    existing_meanings = runtime.repository.list_lexeme_meanings(lexeme.id)
    cor_entries = _load_cor_candidates(runtime, lemma=normalized_lemma, pos_tag=pos_tag)
    senses = _discover_senses(
        runtime,
        lemma=normalized_lemma,
        pos_tag=pos_tag,
        cor_candidates=cor_entries,
    )
    if not senses:
        return ExpandLemmaSensesResult(
            lemma=normalized_lemma,
            status="no_senses",
            discovered_count=0,
            inserted_count=0,
            renamed_legacy=False,
        )

    renamed_legacy = _maybe_rename_legacy_meaning(
        runtime,
        lemma=normalized_lemma,
        existing_meanings=existing_meanings,
        senses=senses,
    )
    refreshed_meanings = runtime.repository.list_lexeme_meanings(lexeme.id)
    existing_keys = {meaning.meaning_key for meaning in refreshed_meanings}

    inserted_count = 0
    for sense in senses:
        if sense.meaning_key in existing_keys:
            continue
        _, inserted = runtime.repository.upsert_lexeme_meaning(
            lexeme_id=lexeme.id,
            meaning_key=sense.meaning_key,
            cor_lemma_idx=None,
            dictionary_status="cor",
            gloss=sense.gloss,
            english_translation=sense.english_translation,
            pos_tag=pos_tag,
            morphology=lexeme.morphology,
        )
        if inserted:
            inserted_count += 1
        existing_keys.add(sense.meaning_key)

    status = "expanded" if inserted_count > 0 or renamed_legacy else "already_expanded"
    return ExpandLemmaSensesResult(
        lemma=normalized_lemma,
        status=status,
        discovered_count=len(senses),
        inserted_count=inserted_count,
        renamed_legacy=renamed_legacy,
    )


def _load_cor_candidates(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    pos_tag: str | None,
) -> list[SenseDiscoveryCorCandidate]:
    entries = runtime.cor.cor_local_entries_for_form(
        form=lemma,
        lemma=lemma,
        preferred_pos_tag=pos_tag,
    )
    candidates: list[SenseDiscoveryCorCandidate] = []
    seen: set[tuple[int | None, str | None]] = set()
    for entry in entries:
        key = (entry.lemma_idx, entry.pos_tag)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(
            SenseDiscoveryCorCandidate(
                cor_id=entry.cor_id,
                lemma=entry.lemma,
                gloss=entry.gloss,
                pos_tag=entry.pos_tag,
                lemma_idx=entry.lemma_idx,
            )
        )
    return candidates


def _discover_senses(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    pos_tag: str | None,
    cor_candidates: list[SenseDiscoveryCorCandidate],
) -> list[DiscoveredSense]:
    payload = SenseDiscoveryInput(
        lemma=lemma,
        pos_tag=pos_tag,
        cor_gloss=None,
        cor_candidates=cor_candidates,
    )
    result = runtime.translation.discover_senses(payload)
    if result is None:
        return []
    return list(result.senses)


def _maybe_rename_legacy_meaning(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    existing_meanings: list,
    senses: list[DiscoveredSense],
) -> bool:
    if len(existing_meanings) != 1:
        return False
    only = existing_meanings[0]
    if normalize_token(only.meaning_key) != normalize_token(lemma):
        return False
    if not senses:
        return False
    primary = _match_sense_for_legacy(only, senses) or senses[0]
    runtime.repository.overwrite_lexeme_meaning_descriptor(
        meaning_id=only.id,
        meaning_key=primary.meaning_key,
        gloss=primary.gloss,
        english_translation=primary.english_translation,
    )
    return True


def _match_sense_for_legacy(
    legacy_meaning,
    senses: list[DiscoveredSense],
) -> DiscoveredSense | None:
    legacy_translation = normalize_token(legacy_meaning.english_translation or "")
    if not legacy_translation:
        return None
    for sense in senses:
        if normalize_token(sense.english_translation) == legacy_translation:
            return sense
    return None

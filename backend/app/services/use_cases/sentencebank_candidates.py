from __future__ import annotations

from dataclasses import dataclass

from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    lookup_translation_for_cor_local_entry,
)
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class SentenceMeaningCandidate:
    id: int
    lemma: str
    meaning_key: str
    cor_lemma_idx: int | None
    gloss: str | None
    english_translation: str | None
    gloss_translation: str | None
    pos_tag: str | None
    morphology: str | None
    cor_id: str | None


@dataclass(frozen=True, slots=True)
class SentenceCandidateResolution:
    candidate: SentenceMeaningCandidate | None
    is_ambiguous: bool
    candidates: tuple[SentenceMeaningCandidate, ...] = ()


def select_sentence_candidate(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
    morphology: str | None,
    sentence_context: str,
) -> SentenceCandidateResolution:
    entries = candidate_entries_for_sentence_token(
        runtime,
        surface_form=surface_form,
        lemma_candidate=lemma_candidate,
        pos_tag=pos_tag,
    )
    if not entries:
        return SentenceCandidateResolution(candidate=None, is_ambiguous=False, candidates=())
    candidates = group_sentence_candidates(
        runtime,
        entries=entries,
        surface_form=surface_form,
        sentence_context=sentence_context,
        morphology=morphology,
    )
    if not candidates:
        return SentenceCandidateResolution(candidate=None, is_ambiguous=False, candidates=())
    if len(candidates) == 1:
        return SentenceCandidateResolution(
            candidate=candidates[0],
            is_ambiguous=False,
            candidates=tuple(candidates),
        )
    return SentenceCandidateResolution(candidate=None, is_ambiguous=True, candidates=tuple(candidates))


def candidate_entries_for_sentence_token(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    lemma_candidate: str,
    pos_tag: str | None,
) -> list[CORLocalEntry]:
    entries: list[CORLocalEntry] = []
    seen: set[str] = set()
    candidate_lemmas = [lemma_candidate]
    if surface_form != lemma_candidate:
        candidate_lemmas.append(surface_form)
    for preferred_pos_tag in (pos_tag, None):
        for lemma in candidate_lemmas:
            for entry in runtime.cor.cor_local_entries_for_form(
                form=surface_form,
                lemma=lemma,
                preferred_pos_tag=preferred_pos_tag,
            ):
                if entry.cor_id in seen:
                    continue
                seen.add(entry.cor_id)
                entries.append(entry)
        for entry in runtime.cor.cor_local_entries_for_surface_form(
            form=surface_form,
            preferred_pos_tag=preferred_pos_tag,
        ):
            if entry.cor_id in seen:
                continue
            seen.add(entry.cor_id)
            entries.append(entry)
        if entries:
            break
    return entries


def group_sentence_candidates(
    runtime: WordbankRuntime,
    *,
    entries: list[CORLocalEntry],
    surface_form: str,
    sentence_context: str,
    morphology: str | None,
) -> list[SentenceMeaningCandidate]:
    grouped: dict[tuple[str, int | None, str | None, str | None], CORLocalEntry] = {}
    for entry in entries:
        key = (
            entry.lemma,
            entry.lemma_idx,
            normalize_token(entry.gloss or "") or None,
            entry.pos_tag,
        )
        grouped.setdefault(key, entry)
    candidates: list[SentenceMeaningCandidate] = []
    for index, entry in enumerate(grouped.values(), start=1):
        english_translation = contextual_translation_for_sentence_candidate(
            runtime,
            surface_form=surface_form,
            sentence_context=sentence_context,
            morphology=morphology,
            entry=entry,
        )
        gloss_translation = runtime.cor.lookup_translation_for_cor_gloss(
            entry=entry,
            lemma_translation=english_translation,
            cache={},
        )
        candidates.append(
            SentenceMeaningCandidate(
                id=index,
                lemma=entry.lemma,
                meaning_key=normalize_token(entry.gloss or "") or entry.lemma,
                cor_lemma_idx=entry.lemma_idx,
                gloss=normalize_token(entry.gloss or "") or None,
                english_translation=english_translation,
                gloss_translation=gloss_translation,
                pos_tag=entry.pos_tag,
                morphology=entry.morphology,
                cor_id=entry.cor_id,
            )
        )
    return candidates


def contextual_translation_for_sentence_candidate(
    runtime: WordbankRuntime,
    *,
    surface_form: str,
    sentence_context: str,
    morphology: str | None,
    entry: CORLocalEntry,
) -> str | None:
    normalized_gloss = normalize_token(entry.gloss or "") or None
    if (entry.pos_tag or "").upper() == "VERB" and normalized_gloss is None:
        return lookup_translation_for_cor_local_entry(runtime.translation, entry)
    contextual = runtime.translation.lookup_contextual_word_translation(
        surface_form=surface_form,
        lemma=entry.lemma,
        pos_tag=entry.pos_tag,
        morphology=morphology or entry.morphology,
        gloss=normalized_gloss,
        sentence_context=sentence_context,
    )
    if contextual.translation:
        return contextual.translation
    return lookup_translation_for_cor_local_entry(runtime.translation, entry)

from __future__ import annotations

import logging
import sqlite3

from app.api.schemas.v1.wordbank import CORSearchVariant, LemmaDetailsResponse
from app.db.repositories import (
    RelatedWordWriteRecord,
    WordbankBackgroundJobRepository,
    WordbankRepository,
)
from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.related_words import GeminiRelatedWordsService, GlossVariantCandidate
from app.services.token_classifier import normalize_token

logger = logging.getLogger(__name__)
from app.services.use_cases.wordbank.collaborators.cor_local import (
    consolidate_cor_local_entries,
    cor_local_variant,
    drop_glossless_when_gloss_exists,
)
from app.services.use_cases.wordbank.collaborators.cor_local_translations import (
    lookup_translation_for_cor_gloss,
)
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.gloss_translations import is_likely_english_gloss

_RELATED_WORDS_JOB_TYPE = "resolve_related_words"
_RELATED_WORDS_RELATION_TYPE = "compound_component"
_REVERSE_RELATED_WORDS_RELATION_TYPE = "compound_host"


def related_words_dedupe_key(stored_lemma: str) -> str:
    return f"{_RELATED_WORDS_JOB_TYPE}::{stored_lemma}"


class RelatedWordsCollaborator:
    def __init__(
        self,
        related_words_service: GeminiRelatedWordsService | None,
        cor_local_lexicon_service: CORLocalLexiconService | None,
        repository: WordbankRepository,
        db_path,
        translation: TranslationCollaborator | None = None,
        owner_user_id: int = 1,
    ) -> None:
        self._related_words_service = related_words_service
        self._cor_local_lexicon_service = cor_local_lexicon_service
        self._repository = repository
        self._jobs = WordbankBackgroundJobRepository(db_path, owner_user_id=owner_user_id)
        self._translation = translation

    def queue_resolution_request(self, *, stored_lemma: str) -> bool:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma or self._related_words_service is None:
            return False
        lexeme = self._repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            return False
        return self._jobs.enqueue(
            job_type=_RELATED_WORDS_JOB_TYPE,
            dedupe_key=related_words_dedupe_key(normalized_lemma),
            payload={"stored_lemma": normalized_lemma},
        )

    def process_queued_resolution(self, *, stored_lemma: str) -> None:
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma or self._related_words_service is None:
            return
        lexeme = self._repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            return
        related_words = self._related_words_service.find_related_words(lemma=normalized_lemma)
        persisted_rows: list[RelatedWordWriteRecord] = []
        for index, item in enumerate(related_words.items):
            normalized_translation = _normalize_related_translation(
                english_translation=item.english_translation,
                pos_tag=item.pos_tag,
            )
            candidates = self._cor_candidates(item.lemma, item.pos_tag)
            if not candidates and lexeme.dictionary_status != "generated_non_cor":
                continue
            self._persist_additional_translation_for_saved_target(
                lemma=item.lemma,
                english_translation=normalized_translation,
            )
            preferred_cor_id = (
                self._pick_preferred_cor_id(
                    lemma=item.lemma,
                    english_translation=normalized_translation,
                    pos_tag=item.pos_tag,
                    cor_candidates=candidates,
                )
                if candidates
                else None
            )
            persisted_rows.append(
                RelatedWordWriteRecord(
                    relation_type=_RELATED_WORDS_RELATION_TYPE,
                    sort_order=index,
                    related_lemma=item.lemma,
                    english_translation=normalized_translation,
                    pos_tag=item.pos_tag,
                    preferred_cor_id=preferred_cor_id,
                )
            )
        self._repository.replace_related_words(
            owner_lexeme_id=lexeme.id,
            items=persisted_rows,
        )
        job = self._jobs.get_by_dedupe_key(related_words_dedupe_key(normalized_lemma))
        if job is not None and job.status in {"pending", "running"}:
            self._jobs.mark_completed(job.id)

    def seed_mwe_component_related_words(self, *, stored_lemma: str) -> None:
        """Write an immediate seed of MWE component words for the UI.

        Does NOT mark the queued Gemini related-words job complete — the worker is
        expected to run and replace these rows with Gemini's richer answer (which
        includes component words + near-synonym compounds). This function only
        provides a synchronous placeholder so the user sees *something* in the
        Related Words section while the background job runs.
        """
        normalized_lemma = normalize_token(stored_lemma)
        if not normalized_lemma or " " not in normalized_lemma:
            return
        lexeme = self._repository.get_lexeme(normalized_lemma)
        if lexeme is None:
            return
        components = [token for token in normalized_lemma.split() if token]
        if not components:
            return
        rows: list[RelatedWordWriteRecord] = []
        for index, component in enumerate(components):
            pos_tag = self._infer_component_pos_tag(component)
            translation = self._infer_component_translation(component, pos_tag)
            rows.append(
                RelatedWordWriteRecord(
                    relation_type=_RELATED_WORDS_RELATION_TYPE,
                    sort_order=index,
                    related_lemma=component,
                    english_translation=translation,
                    pos_tag=pos_tag,
                    preferred_cor_id=None,
                )
            )
        self._repository.replace_related_words(
            owner_lexeme_id=lexeme.id,
            items=rows,
        )

    def _infer_component_pos_tag(self, component: str) -> str | None:
        if self._cor_local_lexicon_service is None:
            return None
        try:
            entries = self._cor_local_lexicon_service.lookup_form(component, limit=50)
        except (FileNotFoundError, sqlite3.OperationalError) as exc:
            logger.warning(
                "mwe_component_pos_lookup_failed",
                extra={"component": component, "error": str(exc)},
            )
            return None
        for entry in entries:
            if normalize_token(entry.lemma) == component and entry.pos_tag:
                return entry.pos_tag
        return entries[0].pos_tag if entries else None

    def _infer_component_translation(self, component: str, pos_tag: str | None) -> str | None:
        target = self._repository.find_saved_lemma_translation_target(component)
        if target is not None and target.english_translation:
            return _normalize_related_translation(
                english_translation=target.english_translation,
                pos_tag=pos_tag,
            )
        return None

    def build_related_words_section(
        self,
        *,
        owner_lexeme_id: int,
        stored_lemma: str,
    ) -> LemmaDetailsResponse.RelatedWordsSection:
        rows = self._repository.list_related_words(owner_lexeme_id)
        reverse_rows = self._repository.list_reverse_related_words(stored_lemma)
        items = [
            item
            for row in [*rows, *reverse_rows]
            if (item := self._build_related_word_item(row)) is not None
        ]
        job = self._jobs.get_by_dedupe_key(related_words_dedupe_key(stored_lemma))
        if job is not None and job.status in {"pending", "running"}:
            return LemmaDetailsResponse.RelatedWordsSection(
                status="queued",
                message="Finding related compound words.",
                items=items,
            )
        if job is not None and job.status == "failed" and not items:
            return LemmaDetailsResponse.RelatedWordsSection(
                status="error",
                message=job.last_error or "Could not resolve related words.",
                items=items,
            )
        if items:
            return LemmaDetailsResponse.RelatedWordsSection(
                status="ready",
                message=None,
                items=items,
            )
        return LemmaDetailsResponse.RelatedWordsSection(
            status="empty",
            message="No related compound words found.",
            items=[],
        )

    def _build_related_word_item(self, row) -> LemmaDetailsResponse.RelatedWord | None:
        variants = self._variants_for_related_word(row.related_lemma, row.pos_tag, row.english_translation)
        if row.relation_type == _REVERSE_RELATED_WORDS_RELATION_TYPE:
            saved_translation_target = self._repository.find_saved_lemma_translation_target(row.related_lemma)
            if saved_translation_target is None:
                return None
            saved_match = LemmaDetailsResponse.RelatedWordSavedMatch(
                status="saved_lemma",
                target_lemma=saved_translation_target.lemma,
                target_meaning_id=saved_translation_target.meaning_id,
            )
        else:
            saved_lemma = self._repository.find_saved_lemma_target(row.related_lemma)
            if saved_lemma is not None:
                saved_match = LemmaDetailsResponse.RelatedWordSavedMatch(
                    status="saved_lemma",
                    target_lemma=saved_lemma.lemma,
                    target_meaning_id=None,
                )
            else:
                saved_variation = self._repository.find_saved_variation_target(row.related_lemma)
                if saved_variation is not None:
                    saved_match = LemmaDetailsResponse.RelatedWordSavedMatch(
                        status="saved_variation",
                        target_lemma=saved_variation.lemma,
                        target_meaning_id=saved_variation.meaning_id,
                    )
                else:
                    saved_match = LemmaDetailsResponse.RelatedWordSavedMatch(status="unsaved")
        display_variant, candidate_variants = _resolve_display_variant(variants, row.preferred_cor_id)
        return LemmaDetailsResponse.RelatedWord(
            id=row.id,
            relation_type=row.relation_type,
            lemma=row.related_lemma,
            english_translation=row.english_translation,
            pos_tag=row.pos_tag,
            saved_match=saved_match,
            display_variant=display_variant,
            candidate_variants=candidate_variants,
        )

    def _variants_for_related_word(
        self,
        lemma: str,
        pos_tag: str | None,
        english_translation: str | None,
    ) -> list[CORSearchVariant]:
        gloss_cache: dict[str, str | None] = {}
        return [
            cor_local_variant(
                entry,
                lemma_translation=english_translation,
                saveable_translation=english_translation,
                gloss_translation=self._resolve_gloss_translation(entry, english_translation, gloss_cache),
            )
            for entry in self._cor_candidates(lemma, pos_tag)
        ]

    def _resolve_gloss_translation(
        self,
        entry: CORLocalEntry,
        lemma_translation: str | None,
        gloss_cache: dict[str, str | None],
    ) -> str | None:
        if not entry.gloss:
            return None
        if is_likely_english_gloss(entry.gloss):
            return entry.gloss
        if self._translation is None:
            return None
        return lookup_translation_for_cor_gloss(
            self._translation,
            entry=entry,
            lemma_translation=lemma_translation,
            gloss_cache=gloss_cache,
        )

    def _cor_candidates(self, lemma: str, pos_tag: str | None) -> list[CORLocalEntry]:
        if self._cor_local_lexicon_service is None:
            return []
        normalized_lemma = normalize_token(lemma)
        if not normalized_lemma:
            return []
        try:
            entries = self._cor_local_lexicon_service.lookup_form(normalized_lemma, limit=200)
        except FileNotFoundError:
            return []
        filtered = [
            entry
            for entry in entries
            if entry.norm == "N" and normalize_token(entry.lemma) == normalized_lemma
        ]
        filtered = consolidate_cor_local_entries(filtered)
        filtered = drop_glossless_when_gloss_exists(filtered)
        if pos_tag is not None:
            filtered = [entry for entry in filtered if entry.pos_tag == pos_tag]
        return filtered

    def _pick_preferred_cor_id(
        self,
        *,
        lemma: str,
        english_translation: str | None,
        pos_tag: str | None,
        cor_candidates: list,
    ) -> str | None:
        if len(cor_candidates) <= 1:
            return None
        if self._related_words_service is None:
            return None
        gloss_cache: dict[str, str | None] = {}
        candidates = [
            GlossVariantCandidate(
                cor_id=entry.cor_id,
                gloss=entry.gloss,
                gloss_translation=self._resolve_gloss_translation(entry, english_translation, gloss_cache),
                gram_raw=entry.gram_raw,
            )
            for entry in cor_candidates
        ]
        try:
            return self._related_words_service.pick_gloss_variant(
                lemma=lemma,
                english_translation=english_translation,
                pos_tag=pos_tag,
                candidates=candidates,
            )
        except Exception:
            return None

    def _persist_additional_translation_for_saved_target(
        self,
        *,
        lemma: str,
        english_translation: str | None,
    ) -> None:
        normalized_translation = normalize_token(english_translation or "")
        if not normalized_translation:
            return
        target = self._repository.find_saved_lemma_translation_target(lemma)
        if target is None:
            target = self._repository.find_saved_variation_translation_target(lemma)
        if target is None:
            return
        if normalize_token(target.english_translation or "") == normalized_translation:
            return
        self._repository.insert_additional_translation(
            lexeme_id=target.lexeme_id,
            meaning_id=target.meaning_id,
            english_translation=normalized_translation,
            source="related_words",
        )


def _resolve_display_variant(
    variants: list[CORSearchVariant],
    preferred_cor_id: str | None,
) -> tuple[CORSearchVariant | None, list[CORSearchVariant]]:
    if len(variants) == 1:
        return variants[0], []
    if not variants:
        return None, []
    if preferred_cor_id is not None:
        matched = next((v for v in variants if v.cor_id == preferred_cor_id), None)
        if matched is not None:
            return matched, []
    return None, variants


def _normalize_related_translation(*, english_translation: str | None, pos_tag: str | None) -> str | None:
    if english_translation is None:
        return None
    normalized = " ".join(english_translation.strip().split())
    if not normalized:
        return None
    if pos_tag != "VERB":
        return normalized
    if normalized.casefold().startswith("to "):
        return normalized
    return f"to {normalized}"

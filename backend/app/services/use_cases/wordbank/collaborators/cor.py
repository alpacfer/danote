from __future__ import annotations

from pathlib import Path

from app.api.schemas.v1.wordbank import (
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    ENSearchFormResponse,
    ResolveQueryResponse,
)
from app.services.cor import COREntry, CORLexiconService
from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.en_gemini_translation import ENGeminiTranslationService
from app.services.en_local import ENLocalLexiconService
from app.services.translation import TranslationService
from app.services.use_cases.wordbank.collaborators.cor_local import (
    best_cor_local_entry_for_form,
    best_cor_local_lemma_entry,
    cor_local_entries_for_form,
    cor_local_entries_for_lemma_idx,
    cor_local_entries_for_surface_form,
    cor_local_entry_for_cor_id,
    lookup_translation_for_cor_gloss,
    search_cor_form,
    search_cor_lemma_paradigm,
)
from app.services.use_cases.wordbank.collaborators.cor_resolution import resolve_query
from app.services.use_cases.wordbank.collaborators.en_resolution import search_en_form
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.shared import _cor_entry_priority


class CorResolutionCollaborator:
    """Owns COR dictionary lookup, query resolution, and COR-local search."""

    def __init__(
        self,
        cor_lexicon_service: CORLexiconService | None,
        cor_local_lexicon_service: CORLocalLexiconService | None,
        db_path: Path,
        translation: TranslationCollaborator,
        nlp: NLPCollaborator,
        *,
        en_local_lexicon_service: ENLocalLexiconService | None = None,
        en_gemini_translation_service: ENGeminiTranslationService | None = None,
        translation_service: TranslationService | None = None,
    ) -> None:
        self._cor_lexicon_service = cor_lexicon_service
        self._cor_local_lexicon_service = cor_local_lexicon_service
        self._db_path = db_path
        self._translation = translation
        self._nlp = nlp
        self._en_local_lexicon_service = en_local_lexicon_service
        self._en_gemini_translation_service = en_gemini_translation_service
        self._translation_service = translation_service

    # ------------------------------------------------------------------
    # Public API — query resolution
    # ------------------------------------------------------------------

    def resolve_query(
        self,
        query_text: str,
        *,
        include_translations: bool = True,
        include_language_detection: bool = True,
    ) -> ResolveQueryResponse:
        return resolve_query(
            db_path=self._db_path,
            translation=self._translation,
            nlp=self._nlp,
            cor_entries_lookup=self.cor_entries_for_surface,
            query_text=query_text,
            include_translations=include_translations,
            include_language_detection=include_language_detection,
            en_local_lexicon_service=self._en_local_lexicon_service,
            en_gemini_translation_service=self._en_gemini_translation_service,
            translation_service=self._translation_service,
        )

    # ------------------------------------------------------------------
    # Public API — COR local search
    # ------------------------------------------------------------------

    def search_cor_form(self, form: str, *, limit: int = 100, include_translations: bool = True) -> CORSearchFormResponse:
        return search_cor_form(
            self._cor_local_lexicon_service,
            self._translation,
            form,
            limit=limit,
            include_translations=include_translations,
        )

    def search_cor_lemma_paradigm(
        self, lemma_idx: int, *, limit: int = 1000
    ) -> CORLemmaParadigmResponse:
        return search_cor_lemma_paradigm(
            self._cor_local_lexicon_service,
            self._translation,
            lemma_idx,
            limit=limit,
        )

    def search_en_form(self, form: str, *, include_translations: bool = True) -> ENSearchFormResponse:
        return search_en_form(
            form=form,
            en_local_lexicon_service=self._en_local_lexicon_service,
            en_gemini_translation_service=self._en_gemini_translation_service,
            translation_service=self._translation_service,
            include_translations=include_translations,
        )

    # ------------------------------------------------------------------
    # Public helpers used by WordbankUseCase directly
    # ------------------------------------------------------------------

    def cor_entries_for_surface(self, normalized_value: str) -> list[COREntry]:
        if self._cor_lexicon_service is None:
            return []
        return self._cor_lexicon_service.lookup_full_form(normalized_value)

    def best_cor_entry(
        self,
        entries: list[COREntry],
        *,
        normalized_surface: str,
        preferred_pos_tag: str | None,
    ) -> COREntry | None:
        if not entries:
            return None
        filtered = entries
        if preferred_pos_tag:
            preferred = [e for e in entries if e.pos_tag == preferred_pos_tag]
            if preferred:
                filtered = preferred
        return min(filtered, key=lambda e: _cor_entry_priority(e, normalized_surface))

    def best_cor_local_entry_for_form(
        self,
        *,
        form: str,
        lemma: str,
        preferred_pos_tag: str | None,
        preferred_lemma_idx: int | None = None,
    ) -> CORLocalEntry | None:
        return best_cor_local_entry_for_form(
            self._cor_local_lexicon_service,
            form=form,
            lemma=lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_lemma_idx=preferred_lemma_idx,
        )

    def cor_local_entries_for_form(
        self,
        *,
        form: str,
        lemma: str,
        preferred_pos_tag: str | None,
        preferred_lemma_idx: int | None = None,
    ) -> list[CORLocalEntry]:
        return cor_local_entries_for_form(
            self._cor_local_lexicon_service,
            form=form,
            lemma=lemma,
            preferred_pos_tag=preferred_pos_tag,
            preferred_lemma_idx=preferred_lemma_idx,
        )

    def cor_local_entries_for_surface_form(
        self,
        *,
        form: str,
        preferred_pos_tag: str | None,
    ) -> list[CORLocalEntry]:
        return cor_local_entries_for_surface_form(
            self._cor_local_lexicon_service,
            form=form,
            preferred_pos_tag=preferred_pos_tag,
        )

    def best_cor_local_lemma_entry(
        self,
        *,
        lemma_idx: int,
        lemma: str,
        preferred_pos_tag: str | None,
        allow_lemma_mismatch: bool = False,
    ) -> CORLocalEntry | None:
        return best_cor_local_lemma_entry(
            self._cor_local_lexicon_service,
            lemma_idx=lemma_idx,
            lemma=lemma,
            preferred_pos_tag=preferred_pos_tag,
            allow_lemma_mismatch=allow_lemma_mismatch,
        )

    def cor_local_entries_for_lemma_idx(
        self,
        *,
        lemma_idx: int,
        lemma: str,
        preferred_pos_tag: str | None,
    ) -> list[CORLocalEntry]:
        return cor_local_entries_for_lemma_idx(
            self._cor_local_lexicon_service,
            lemma_idx=lemma_idx,
            lemma=lemma,
            preferred_pos_tag=preferred_pos_tag,
        )

    def cor_local_entry_for_cor_id(self, *, cor_id: str) -> CORLocalEntry | None:
        return cor_local_entry_for_cor_id(
            self._cor_local_lexicon_service,
            cor_id=cor_id,
        )

    def lookup_translation_for_cor_gloss(
        self,
        *,
        entry: CORLocalEntry,
        lemma_translation: str | None = None,
        cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None] | None = None,
    ) -> str | None:
        return lookup_translation_for_cor_gloss(
            self._translation,
            entry=entry,
            lemma_translation=lemma_translation,
            cache=cache,
        )

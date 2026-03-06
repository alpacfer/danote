from __future__ import annotations

from app.api.schemas.v1.wordbank import CORLemmaParadigmResponse, CORSearchFormResponse, CORSearchGroup
from app.services.token_classifier import normalize_token


class WordbankQueriesCorMixin:
    def search_cor_form(self, form: str, *, limit: int = 100) -> CORSearchFormResponse:
        normalized_form = normalize_token(form)
        if not normalized_form:
            raise ValueError("form is required")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if self._cor_local_lexicon_service is None:
            raise RuntimeError("COR local lookup service is unavailable.")

        try:
            entries = self._cor_local_lexicon_service.lookup_form(normalized_form, limit=limit)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "COR local database is unavailable. Build backend/resources/dictionaries/cor.sqlite first."
            ) from exc
        entries = [entry for entry in entries if entry.norm == "N"]
        entries = self._consolidate_cor_local_entries(entries)
        entries = self._drop_glossless_when_gloss_exists(entries)

        groups: list[CORSearchGroup] = []
        lemma_translation_cache: dict[str, str | None] = {}
        gloss_translation_cache: dict[str, str | None] = {}
        grouped: dict[tuple[str, str | None, str | None], int] = {}
        for entry in entries:
            key = (entry.lemma, entry.gloss, entry.pos_tag)
            group_index = grouped.get(key)
            lemma_translation = self._lookup_translation_for_cor_local_entry(entry, lemma_translation_cache)
            gloss_translation = self._lookup_translation_for_cor_gloss(entry.gloss, gloss_translation_cache)
            if group_index is None:
                groups.append(
                    CORSearchGroup(
                        lemma=entry.lemma,
                        gloss=entry.gloss,
                        pos_tag=entry.pos_tag,
                        variants=[
                            self._cor_local_variant(
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
                self._cor_local_variant(
                    entry,
                    lemma_translation=lemma_translation,
                    gloss_translation=gloss_translation,
                )
            )

        return CORSearchFormResponse(
            form=normalized_form,
            groups=groups,
        )



    def search_cor_lemma_paradigm(self, lemma_idx: int, *, limit: int = 1000) -> CORLemmaParadigmResponse:
        if lemma_idx < 1:
            raise ValueError("lemma_idx must be >= 1")
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if self._cor_local_lexicon_service is None:
            raise RuntimeError("COR local lookup service is unavailable.")

        try:
            entries = self._cor_local_lexicon_service.lookup_lemma(lemma_idx, limit=limit)
        except FileNotFoundError as exc:
            raise RuntimeError(
                "COR local database is unavailable. Build backend/resources/dictionaries/cor.sqlite first."
            ) from exc
        entries = [entry for entry in entries if entry.norm == "N"]
        entries = self._consolidate_cor_local_entries(entries)
        entries = self._drop_glossless_when_gloss_exists(entries)

        lemma_translation_cache: dict[str, str | None] = {}
        gloss_translation_cache: dict[str, str | None] = {}
        return CORLemmaParadigmResponse(
            lemma_idx=lemma_idx,
            variants=[
                self._cor_local_variant(
                    entry,
                    lemma_translation=self._lookup_translation_for_cor_local_entry(entry, lemma_translation_cache),
                    gloss_translation=self._lookup_translation_for_cor_gloss(entry.gloss, gloss_translation_cache),
                )
                for entry in entries
            ],
        )



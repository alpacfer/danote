from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import (
    AddWordResponse,
    ApplyVerificationChangesResponse,
    CORLemmaParadigmResponse,
    CORSearchFormResponse,
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GeneratePronunciationResponse,
    GenerateReverseTranslationResponse,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    LemmaSummary,
    ResetDatabaseResponse,
    ResolveQueryResponse,
    VerifyWordResponse,
    WordbankSearchItem,
    WordbankSearchResponse,
)
from app.db.migrations import apply_migrations, get_connection
from app.nlp.adapter import NLPAdapter
from app.services.cor import CORLexiconService
from app.services.cor_local import CORLocalLexiconService
from app.services.token_classifier import normalize_token
from app.services.translation import TranslationService
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.collaborators.pronunciation import PronunciationCollaborator
from app.services.use_cases.wordbank.collaborators.translation import TranslationCollaborator
from app.services.use_cases.wordbank.collaborators.verification import VerificationCollaborator
from app.services.verification import WordVerificationService


class WordbankUseCase:
    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        cor_lexicon_service: CORLexiconService | None = None,
        cor_local_lexicon_service: CORLocalLexiconService | None = None,
        verification_service: WordVerificationService | None = None,
        tts_service: TTSService | None = None,
        gemini_changes_log_path: Path | None = None,
    ):
        self._db_path = db_path
        self._nlp = NLPCollaborator(nlp_adapter, typo_engine, cor_lexicon_service)
        self._pronunciation = PronunciationCollaborator(tts_service, db_path)
        self._translation = TranslationCollaborator(translation_service, db_path)
        self._cor = CorResolutionCollaborator(
            cor_lexicon_service,
            cor_local_lexicon_service,
            db_path,
            self._translation,
            self._nlp,
        )
        self._verification = VerificationCollaborator(
            verification_service,
            db_path,
            gemini_changes_log_path,
            self._nlp,
        )

    # ------------------------------------------------------------------
    # Commands — word addition
    # ------------------------------------------------------------------

    def add_word(
        self,
        surface_token: str,
        lemma_candidate: str | None,
        *,
        pos_tag: str | None = None,
        morphology: str | None = None,
    ) -> AddWordResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not stored_lemma:
            raise ValueError("surface_token or lemma_candidate is required")

        selected_pos_tag = self._nlp.normalize_optional_pos_tag(pos_tag)
        selected_morphology = self._nlp.normalize_optional_morphology(morphology)
        inserted_lexeme = False
        inserted_surface_form = False
        inserted_lemma_surface_form = False
        lemma_translation = self._translation.lookup_translation(stored_lemma)
        surface_translation = (
            self._translation.lookup_translation(normalized_surface) if normalized_surface else None
        )
        lemma_pos_tag, lemma_morphology = self._nlp.extract_pos_and_morphology(
            stored_lemma,
            preferred_pos_tag=selected_pos_tag,
        )
        if lemma_pos_tag is None and selected_pos_tag is not None:
            lemma_pos_tag = selected_pos_tag
        if lemma_morphology is None and selected_morphology is not None:
            lemma_morphology = selected_morphology
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if normalized_surface:
            if selected_pos_tag is not None or selected_morphology is not None:
                surface_pos_tag = selected_pos_tag
                surface_morphology = selected_morphology
            else:
                surface_pos_tag, surface_morphology = self._nlp.extract_pos_and_morphology(
                    normalized_surface,
                    preferred_pos_tag=selected_pos_tag,
                )
        provider = self._translation.provider_name()

        with get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO lexemes (
                    lemma,
                    source,
                    english_translation,
                    translation_provider,
                    pos_tag,
                    morphology
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_lemma,
                    "manual",
                    lemma_translation,
                    provider if lemma_translation else None,
                    lemma_pos_tag,
                    lemma_morphology,
                ),
            )
            inserted_lexeme = cursor.rowcount == 1

            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ?",
                (stored_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise RuntimeError("Failed to create or load lexeme")

            if lemma_translation:
                conn.execute(
                    """
                    UPDATE lexemes
                    SET english_translation = ?, translation_provider = ?
                    WHERE id = ?
                    """,
                    (lemma_translation, provider, lexeme_row["id"]),
                )

            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = COALESCE(pos_tag, ?),
                    morphology = COALESCE(morphology, ?)
                WHERE id = ?
                """,
                (lemma_pos_tag, lemma_morphology, lexeme_row["id"]),
            )

            if normalized_surface and normalized_surface != stored_lemma:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (
                        lexeme_id,
                        form,
                        source,
                        english_translation,
                        translation_provider,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_row["id"],
                        stored_lemma,
                        "manual",
                        lemma_translation,
                        provider if lemma_translation else None,
                        lemma_pos_tag,
                        lemma_morphology,
                    ),
                )
                inserted_lemma_surface_form = cursor.rowcount == 1
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET seen_count = seen_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lexeme_row["id"], stored_lemma),
                )
                if lemma_translation:
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET english_translation = ?, translation_provider = ?
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (lemma_translation, provider, lexeme_row["id"], stored_lemma),
                    )
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lemma_pos_tag, lemma_morphology, lexeme_row["id"], stored_lemma),
                )

            if normalized_surface:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (
                        lexeme_id,
                        form,
                        source,
                        english_translation,
                        translation_provider,
                        pos_tag,
                        morphology
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lexeme_row["id"],
                        normalized_surface,
                        "manual",
                        surface_translation,
                        provider if surface_translation else None,
                        surface_pos_tag,
                        surface_morphology,
                    ),
                )
                inserted_surface_form = cursor.rowcount == 1
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET seen_count = seen_count + 1,
                        last_seen_at = CURRENT_TIMESTAMP
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (lexeme_row["id"], normalized_surface),
                )
                if surface_translation:
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET english_translation = ?, translation_provider = ?
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (surface_translation, provider, lexeme_row["id"], normalized_surface),
                    )
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET pos_tag = COALESCE(pos_tag, ?),
                        morphology = COALESCE(morphology, ?)
                    WHERE lexeme_id = ? AND form = ?
                    """,
                    (surface_pos_tag, surface_morphology, lexeme_row["id"], normalized_surface),
                )

        self._nlp.invalidate_pos_cache(stored_lemma, normalized_surface)

        inserted = inserted_lexeme or inserted_surface_form or inserted_lemma_surface_form
        if inserted:
            self._nlp.add_user_lexeme(stored_lemma)

        status: Literal["inserted", "exists"] = "inserted" if inserted else "exists"
        message = (
            f"Added '{stored_lemma}' to wordbank."
            if inserted
            else f"'{stored_lemma}' is already in the wordbank."
        )
        verification = self._verification.queued_verification_result()

        return AddWordResponse(
            status=status,
            stored_lemma=stored_lemma,
            stored_surface_form=normalized_surface or None,
            source="manual",
            message=message,
            verification=verification,
        )

    # ------------------------------------------------------------------
    # Commands — pronunciation
    # ------------------------------------------------------------------

    def generate_pronunciation_for_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        force: bool = False,
    ) -> GeneratePronunciationResponse:
        return self._pronunciation.generate_pronunciation_for_added_word(
            stored_lemma, stored_surface_form, force=force
        )

    # ------------------------------------------------------------------
    # Commands — verification
    # ------------------------------------------------------------------

    def verify_added_word(
        self, stored_lemma: str, stored_surface_form: str | None
    ) -> VerifyWordResponse:
        return self._verification.verify_added_word(stored_lemma, stored_surface_form)

    def apply_verification_changes(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        suggested_changes: dict[str, str | None],
        provider: str | None = None,
    ) -> ApplyVerificationChangesResponse:
        return self._verification.apply_verification_changes(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            suggested_changes=suggested_changes,
            provider=provider,
        )

    # ------------------------------------------------------------------
    # Commands — database
    # ------------------------------------------------------------------

    def reset_database(self) -> ResetDatabaseResponse:
        if self._db_path.exists():
            os.remove(self._db_path)
        apply_migrations(self._db_path)
        self._nlp.invalidate_typo_cache()
        return ResetDatabaseResponse(
            status="reset",
            message="Database reset complete.",
        )

    # ------------------------------------------------------------------
    # Queries — lemmas
    # ------------------------------------------------------------------

    def list_lemmas(self) -> LemmaListResponse:
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                SELECT
                    l.lemma,
                    l.english_translation AS english_translation,
                    l.pos_tag AS pos_tag,
                    COUNT(sf.id) AS variation_count
                FROM lexemes l
                LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                GROUP BY l.id, l.lemma
                ORDER BY l.lemma COLLATE NOCASE
                """
            ).fetchall()

        return LemmaListResponse(
            items=[
                LemmaSummary(
                    lemma=row["lemma"],
                    display_lemma=self._display_lemma_for_list(row["lemma"], row["pos_tag"]),
                    english_translation=row["english_translation"],
                    variation_count=int(row["variation_count"]),
                )
                for row in rows
            ]
        )

    def search_lemmas(self, query: str, *, limit: int = 8) -> WordbankSearchResponse:
        normalized_query = normalize_token(query)
        if not normalized_query:
            raise ValueError("query is required")
        if limit < 1:
            raise ValueError("limit must be at least 1")

        contains_pattern = f"%{normalized_query}%"
        prefix_pattern = f"{normalized_query}%"
        with get_connection(self._db_path) as conn:
            rows = conn.execute(
                """
                WITH search_candidates AS (
                    SELECT
                        l.id AS lexeme_id,
                        l.lemma AS lemma,
                        l.english_translation AS english_translation,
                        l.pos_tag AS pos_tag,
                        l.morphology AS morphology,
                        (
                            SELECT COUNT(*)
                            FROM surface_forms sf_all
                            WHERE sf_all.lexeme_id = l.id
                        ) AS variation_count,
                        (
                            SELECT sf_match.form
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface,
                        (
                            SELECT sf_match.pos_tag
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface_pos_tag,
                        (
                            SELECT sf_match.morphology
                            FROM surface_forms sf_match
                            WHERE
                                sf_match.lexeme_id = l.id
                                AND sf_match.form LIKE ? COLLATE NOCASE
                            ORDER BY
                                CASE
                                    WHEN sf_match.form = ? COLLATE NOCASE THEN 0
                                    WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                                    ELSE 2
                                END,
                                sf_match.form COLLATE NOCASE
                            LIMIT 1
                        ) AS match_surface_morphology,
                        EXISTS(
                            SELECT 1
                            FROM surface_forms sf_exact
                            WHERE
                                sf_exact.lexeme_id = l.id
                                AND sf_exact.form = ? COLLATE NOCASE
                        ) AS has_surface_exact_match,
                        EXISTS(
                            SELECT 1
                            FROM surface_forms sf_prefix
                            WHERE
                                sf_prefix.lexeme_id = l.id
                                AND sf_prefix.form LIKE ? COLLATE NOCASE
                        ) AS has_surface_prefix_match
                    FROM lexemes l
                    WHERE
                        l.lemma LIKE ? COLLATE NOCASE
                        OR COALESCE(l.english_translation, '') LIKE ? COLLATE NOCASE
                        OR EXISTS(
                            SELECT 1
                            FROM surface_forms sf_contains
                            WHERE
                                sf_contains.lexeme_id = l.id
                                AND sf_contains.form LIKE ? COLLATE NOCASE
                        )
                )
                SELECT
                    lemma,
                    english_translation,
                    COALESCE(match_surface_pos_tag, pos_tag) AS pos_tag,
                    COALESCE(match_surface_morphology, morphology) AS morphology,
                    variation_count,
                    match_surface,
                    has_surface_exact_match,
                    has_surface_prefix_match
                FROM search_candidates
                ORDER BY
                    CASE
                        WHEN lemma = ? COLLATE NOCASE THEN 0
                        WHEN has_surface_exact_match = 1 THEN 1
                        WHEN lemma LIKE ? COLLATE NOCASE THEN 2
                        WHEN has_surface_prefix_match = 1 THEN 3
                        WHEN COALESCE(english_translation, '') LIKE ? COLLATE NOCASE THEN 4
                        ELSE 5
                    END,
                    lemma COLLATE NOCASE
                LIMIT ?
                """,
                (
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    normalized_query,
                    prefix_pattern,
                    contains_pattern,
                    contains_pattern,
                    contains_pattern,
                    normalized_query,
                    prefix_pattern,
                    prefix_pattern,
                    limit,
                ),
            ).fetchall()

        return WordbankSearchResponse(
            items=[
                WordbankSearchItem(
                    lemma=row["lemma"],
                    display_lemma=self._display_lemma_for_list(row["lemma"], row["pos_tag"]),
                    english_translation=row["english_translation"],
                    variation_count=int(row["variation_count"]),
                    match_surface=row["match_surface"],
                    pos_tag=row["pos_tag"],
                    morphology=row["morphology"],
                )
                for row in rows
            ]
        )

    def get_lemma_details(self, lemma: str) -> LemmaDetailsResponse:
        normalized_lemma = normalize_token(lemma)
        if not normalized_lemma:
            raise ValueError("lemma is required")

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, lemma, english_translation AS english_translation, pos_tag, morphology
                FROM lexemes
                WHERE lemma = ?
                """,
                (normalized_lemma,),
            ).fetchone()

            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")

            form_rows = conn.execute(
                """
                SELECT
                    form,
                    english_translation AS english_translation,
                    pos_tag,
                    morphology,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM surface_forms
                WHERE lexeme_id = ?
                ORDER BY form COLLATE NOCASE
                """,
                (lexeme_row["id"],),
            ).fetchall()

        lemma_pos_tag = lexeme_row["pos_tag"]
        lemma_morphology = lexeme_row["morphology"]
        if lemma_pos_tag is None and lemma_morphology is None:
            lemma_pos_tag, lemma_morphology = self._nlp.extract_pos_and_morphology(
                lexeme_row["lemma"]
            )
            self._store_lexeme_metadata(lexeme_row["id"], lemma_pos_tag, lemma_morphology)

        uncached_forms = [
            row["form"]
            for row in form_rows
            if row["pos_tag"] is None and row["morphology"] is None
        ]
        extracted_forms = self._nlp.extract_pos_and_morphology_batch(uncached_forms)
        gloss_translation_cache: dict[str, str | None] = {}

        surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = []
        for row in form_rows:
            pos_tag = row["pos_tag"]
            morphology = row["morphology"]
            if pos_tag is None and morphology is None:
                pos_tag, morphology = extracted_forms.get(row["form"], (None, None))
                self._store_surface_form_metadata(lexeme_row["id"], row["form"], pos_tag, morphology)
            cor_local_entry = self._cor.best_cor_local_entry_for_form(
                form=row["form"],
                lemma=lexeme_row["lemma"],
                preferred_pos_tag=pos_tag,
            )
            gram_raw = cor_local_entry.gram_raw if cor_local_entry is not None else None
            gloss = cor_local_entry.gloss if cor_local_entry is not None else None
            gloss_translation = self._cor.lookup_translation_for_cor_gloss(
                gloss, gloss_translation_cache
            )
            surface_forms.append(
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row["form"],
                    english_translation=row["english_translation"],
                    pos_tag=pos_tag,
                    morphology=morphology,
                    lemma=lexeme_row["lemma"],
                    lemma_translation=lexeme_row["english_translation"],
                    gloss=gloss,
                    gloss_translation=gloss_translation,
                    gram_raw=gram_raw,
                    has_pronunciation=bool(row["has_pronunciation"]),
                )
            )

        return LemmaDetailsResponse(
            lemma=lexeme_row["lemma"],
            english_translation=lexeme_row["english_translation"],
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
            surface_forms=surface_forms,
        )

    # ------------------------------------------------------------------
    # Queries — pronunciation audio
    # ------------------------------------------------------------------

    def get_pronunciation_audio(self, form: str) -> PronunciationAudio:
        return self._pronunciation.get_pronunciation_audio(form)

    # ------------------------------------------------------------------
    # Queries — COR
    # ------------------------------------------------------------------

    def search_cor_form(self, form: str, *, limit: int = 100) -> CORSearchFormResponse:
        return self._cor.search_cor_form(form, limit=limit)

    def search_cor_lemma_paradigm(
        self, lemma_idx: int, *, limit: int = 1000
    ) -> CORLemmaParadigmResponse:
        return self._cor.search_cor_lemma_paradigm(lemma_idx, limit=limit)

    def resolve_query(
        self,
        query_text: str,
        *,
        include_translations: bool = True,
        include_language_detection: bool = True,
    ) -> ResolveQueryResponse:
        return self._cor.resolve_query(
            query_text,
            include_translations=include_translations,
            include_language_detection=include_language_detection,
        )

    # ------------------------------------------------------------------
    # Queries — translation & language detection
    # ------------------------------------------------------------------

    def generate_translation(
        self, surface_token: str, lemma_candidate: str | None
    ) -> GenerateTranslationResponse:
        return self._translation.generate_translation(surface_token, lemma_candidate)

    def generate_phrase_translation(self, source_text: str) -> GeneratePhraseTranslationResponse:
        return self._translation.generate_phrase_translation(source_text)

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        return self._translation.generate_reverse_translation(source_word)

    def detect_word_language(self, source_word: str) -> DetectWordLanguageResponse:
        return self._translation.detect_word_language(
            source_word,
            cor_entries_lookup=self._cor.cor_entries_for_surface,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _display_lemma_for_list(self, lemma: str, pos_tag: str | None) -> str:
        if pos_tag is None:
            pos_tag, _morphology = self._nlp.extract_pos_and_morphology(lemma)
        if pos_tag in {"VERB", "AUX"}:
            return f"at {lemma}"
        return lemma

    def _store_lexeme_metadata(
        self, lexeme_id: int, pos_tag: str | None, morphology: str | None
    ) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE lexemes SET pos_tag = ?, morphology = ? WHERE id = ?",
                (pos_tag, morphology, lexeme_id),
            )

    def _store_surface_form_metadata(
        self,
        lexeme_id: int,
        form: str,
        pos_tag: str | None,
        morphology: str | None,
    ) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                "UPDATE surface_forms SET pos_tag = ?, morphology = ? WHERE lexeme_id = ? AND form = ?",
                (pos_tag, morphology, lexeme_id, form),
            )

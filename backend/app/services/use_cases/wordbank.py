from __future__ import annotations

import json
import logging
import os
import sqlite3
import io
import wave
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from app.api.schemas.v1.wordbank import (
    AddWordResponse,
    ApplyVerificationChangesResponse,
    DetectWordLanguageResponse,
    GeneratePronunciationResponse,
    GeneratePhraseTranslationResponse,
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
    WordActionSuggestion,
)
from app.db.migrations import apply_migrations, get_connection
from app.nlp.adapter import NLPAdapter
from app.nlp.token_filter import is_short_letter_word, is_wordlike_token
from app.services.text_preprocessing import strip_inline_comments
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.translation import TranslationService
from app.services.tts import PronunciationAudio, TTSService
from app.services.verification import WordVerificationInput, WordVerificationService

logger = logging.getLogger(__name__)


def _looks_like_wav(payload: bytes) -> bool:
    return len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WAVE"


def _pcm_to_wav_bytes(pcm_data: bytes, *, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def _is_pcm_like_mime(mime_type: str | None) -> bool:
    if not isinstance(mime_type, str):
        return False
    normalized = mime_type.strip().lower()
    return normalized.startswith("audio/pcm") or normalized.startswith("audio/l16") or "codec=pcm" in normalized


def _normalize_pronunciation_audio(audio: PronunciationAudio) -> PronunciationAudio:
    normalized_mime = audio.mime_type.strip().lower() if isinstance(audio.mime_type, str) else ""
    if _is_pcm_like_mime(normalized_mime):
        return PronunciationAudio(audio_bytes=_pcm_to_wav_bytes(audio.audio_bytes), mime_type="audio/wav")
    if _looks_like_wav(audio.audio_bytes):
        return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type="audio/wav")
    if normalized_mime:
        return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type=normalized_mime)
    return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type="audio/wav")


def _normalize_action_value(value: str) -> str:
    return " ".join(value.strip().lower().split())


def build_word_action_suggestions(
    *,
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"],
    query_surface: str,
    query_lemma: str | None,
    query_pos_tag: str | None,
    query_morphology: str | None,
    matched_lemma: str | None,
    da_to_en_translation: str | None,
    en_to_da_translation: str | None,
    en_to_da_lemma: str | None,
    en_to_da_pos_tag: str | None,
    en_to_da_morphology: str | None,
    query_language: Literal["en", "da", "ambiguous"] | None,
    query_language_confidence: float | None,
) -> list[WordActionSuggestion]:
    query_surface_clean = query_surface.strip()
    query_lemma_clean = query_lemma.strip() if query_lemma else ""
    actions: list[WordActionSuggestion] = []

    if classification == "known":
        known_lemma = matched_lemma or query_lemma_clean or query_surface_clean
        if known_lemma:
            actions.append(
                WordActionSuggestion(
                    action_type="open_wordbank",
                    surface=query_surface_clean,
                    lemma=known_lemma,
                    direction="known",
                    direction_label="Wordbank",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                )
            )
        return actions

    if classification == "variation" and matched_lemma:
        if _normalize_action_value(query_surface_clean) != _normalize_action_value(matched_lemma):
            actions.append(
                WordActionSuggestion(
                    action_type="add_variation",
                    surface=query_surface_clean,
                    lemma=matched_lemma,
                    translation_label=query_surface_clean,
                    direction="variation",
                    direction_label="Variation",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                )
            )
        return actions

    if classification == "typo_likely" and not da_to_en_translation and not en_to_da_translation:
        return []

    if query_surface_clean:
        lemma_value = query_lemma_clean or query_surface_clean
        if da_to_en_translation or not en_to_da_translation:
            actions.append(
                WordActionSuggestion(
                    action_type="add_as_new",
                    surface=query_surface_clean,
                    lemma=lemma_value,
                    translation_label=da_to_en_translation or query_surface_clean,
                    direction="da_to_en",
                    direction_label="Danish -> English",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                    show_lemma=_normalize_action_value(query_surface_clean) != _normalize_action_value(lemma_value),
                )
            )

    if en_to_da_translation and not (query_language == "da" and (query_language_confidence or 0) >= 0.7):
        is_duplicate = any(_normalize_action_value(item.surface) == _normalize_action_value(en_to_da_translation) for item in actions)
        if not is_duplicate:
            en_lemma = (en_to_da_lemma or en_to_da_translation).strip()
            actions.append(
                WordActionSuggestion(
                    action_type="add_as_new",
                    surface=en_to_da_translation,
                    lemma=en_lemma,
                    translation_label=en_to_da_translation,
                    direction="en_to_da",
                    direction_label="English -> Danish",
                    pos_tag=en_to_da_pos_tag,
                    morphology=en_to_da_morphology,
                    show_lemma=_normalize_action_value(en_to_da_translation) != _normalize_action_value(en_lemma),
                )
            )

    return actions


class WordbankUseCase:
    _AMBIGUOUS_SHORT_WORDS = frozenset(
        {
            "an",
            "at",
            "de",
            "den",
            "det",
            "en",
            "for",
            "gift",
            "i",
            "in",
            "is",
            "it",
            "to",
        }
    )

    def __init__(
        self,
        db_path,
        typo_engine=None,
        translation_service: TranslationService | None = None,
        nlp_adapter: NLPAdapter | None = None,
        verification_service: WordVerificationService | None = None,
        tts_service: TTSService | None = None,
        gemini_changes_log_path: Path | None = None,
    ):
        self._db_path = db_path
        self._typo_engine = typo_engine
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._verification_service = verification_service
        self._tts_service = tts_service
        self._gemini_changes_log_path = gemini_changes_log_path
        self._pos_morph_cache: dict[str, tuple[str | None, str | None]] = {}

    def add_word(self, surface_token: str, lemma_candidate: str | None) -> AddWordResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not stored_lemma:
            raise ValueError("surface_token or lemma_candidate is required")

        inserted_lexeme = False
        inserted_surface_form = False
        lemma_translation = self._lookup_translation(stored_lemma)
        surface_translation = self._lookup_translation(normalized_surface) if normalized_surface else None
        lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(stored_lemma)
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if normalized_surface:
            surface_pos_tag, surface_morphology = self._extract_pos_and_morphology(normalized_surface)
        provider = self._translation_provider_name()

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

        self._invalidate_pos_cache(stored_lemma, normalized_surface)

        inserted = inserted_lexeme or inserted_surface_form
        if self._typo_engine is not None and inserted:
            self._typo_engine.add_user_lexeme(stored_lemma)

        status: Literal["inserted", "exists"] = "inserted" if inserted else "exists"
        message = (
            f"Added '{stored_lemma}' to wordbank."
            if inserted
            else f"'{stored_lemma}' is already in the wordbank."
        )
        verification = self._queued_verification_result()

        return AddWordResponse(
            status=status,
            stored_lemma=stored_lemma,
            stored_surface_form=normalized_surface or None,
            source="manual",
            message=message,
            verification=verification,
        )

    def generate_pronunciation_for_added_word(
        self,
        stored_lemma: str,
        stored_surface_form: str | None,
        *,
        force: bool = False,
    ) -> GeneratePronunciationResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        pronunciation_form = normalized_surface or normalized_lemma
        forms_to_generate = [normalized_lemma]
        if normalized_surface and normalized_surface != normalized_lemma:
            forms_to_generate.append(normalized_surface)
        if not pronunciation_form:
            return GeneratePronunciationResponse(
                status="skipped",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                pronunciation_form=None,
            )

        if self._tts_service is None:
            return GeneratePronunciationResponse(
                status="unavailable",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                pronunciation_form=pronunciation_form,
            )

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                "SELECT id FROM lexemes WHERE lemma = ? LIMIT 1",
                (normalized_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")
            generated_any = False
            for form in forms_to_generate:
                generated_now = self._ensure_surface_pronunciation(
                    conn=conn,
                    lexeme_id=int(lexeme_row["id"]),
                    form=form,
                    force=force,
                )
                generated_any = generated_any or generated_now
            row = conn.execute(
                """
                SELECT pronunciation_audio
                FROM surface_forms
                WHERE lexeme_id = ? AND form = ?
                LIMIT 1
                """,
                (int(lexeme_row["id"]), pronunciation_form),
            ).fetchone()

        has_audio = bool(row is not None and isinstance(row["pronunciation_audio"], bytes) and row["pronunciation_audio"])
        if force and not generated_any:
            status: Literal["generated", "unavailable", "skipped"] = "unavailable"
        else:
            status = "generated" if has_audio else "unavailable"
        return GeneratePronunciationResponse(
            status=status,
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            pronunciation_form=pronunciation_form,
        )

    def verify_added_word(self, stored_lemma: str, stored_surface_form: str | None) -> VerifyWordResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        payload = self._build_verification_input(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
        )
        verification = self._verify_added_word(payload)
        return VerifyWordResponse(
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            verification=verification,
        )

    def apply_verification_changes(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
        suggested_changes: dict[str, str | None],
        provider: str | None = None,
    ) -> ApplyVerificationChangesResponse:
        normalized_lemma = normalize_token(stored_lemma)
        normalized_surface = normalize_token(stored_surface_form or "") or None
        if not normalized_lemma:
            raise ValueError("stored_lemma is required")

        accepted_fields = (
            "lemma_pos_tag",
            "lemma_morphology",
            "surface_pos_tag",
            "surface_morphology",
            "lexeme_translation",
            "surface_translation",
        )
        normalized_changes: dict[str, str] = {}
        for field in accepted_fields:
            value = suggested_changes.get(field)
            if not isinstance(value, str):
                continue
            cleaned = value.strip()
            if cleaned:
                if field in {"lexeme_translation", "surface_translation"}:
                    cleaned = self._normalize_translation_value(cleaned) or ""
                    if not cleaned:
                        continue
                normalized_changes[field] = cleaned

        if not normalized_changes:
            return ApplyVerificationChangesResponse(
                status="skipped",
                stored_lemma=normalized_lemma,
                stored_surface_form=normalized_surface,
                applied_fields=[],
            )

        needs_surface = any(
            field in normalized_changes
            for field in ("surface_pos_tag", "surface_morphology", "surface_translation")
        )
        if needs_surface and not normalized_surface:
            raise ValueError("stored_surface_form is required for surface-level verification changes.")

        provider_name = provider.strip().lower() if isinstance(provider, str) and provider.strip() else "verification"
        applied_fields: list[str] = []
        lexeme_before: dict[str, str | None] | None = None
        surface_before: dict[str, str | None] | None = None

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, pos_tag, morphology, english_translation, translation_provider
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (normalized_lemma,),
            ).fetchone()
            if lexeme_row is None:
                raise LookupError(f"Lemma '{normalized_lemma}' was not found")
            lexeme_id = int(lexeme_row["id"])
            lexeme_before = {
                "pos_tag": lexeme_row["pos_tag"],
                "morphology": lexeme_row["morphology"],
                "english_translation": lexeme_row["english_translation"],
                "translation_provider": lexeme_row["translation_provider"],
            }

            lexeme_updates: list[str] = []
            lexeme_params: list[str | int] = []
            if "lemma_pos_tag" in normalized_changes:
                lexeme_updates.append("pos_tag = ?")
                lexeme_params.append(normalized_changes["lemma_pos_tag"])
                applied_fields.append("lemma_pos_tag")
            if "lemma_morphology" in normalized_changes:
                lexeme_updates.append("morphology = ?")
                lexeme_params.append(normalized_changes["lemma_morphology"])
                applied_fields.append("lemma_morphology")
            if "lexeme_translation" in normalized_changes:
                lexeme_updates.append("english_translation = ?")
                lexeme_updates.append("translation_provider = ?")
                lexeme_params.append(normalized_changes["lexeme_translation"])
                lexeme_params.append(provider_name)
                applied_fields.append("lexeme_translation")

            if lexeme_updates:
                conn.execute(
                    f"UPDATE lexemes SET {', '.join(lexeme_updates)} WHERE id = ?",
                    (*lexeme_params, lexeme_id),
                )

            if normalized_surface:
                surface_row = conn.execute(
                    """
                    SELECT pos_tag, morphology, english_translation, translation_provider
                    FROM surface_forms
                    WHERE lexeme_id = ? AND form = ?
                    LIMIT 1
                    """,
                    (lexeme_id, normalized_surface),
                ).fetchone()
                if surface_row is not None:
                    surface_before = {
                        "pos_tag": surface_row["pos_tag"],
                        "morphology": surface_row["morphology"],
                        "english_translation": surface_row["english_translation"],
                        "translation_provider": surface_row["translation_provider"],
                    }
                conn.execute(
                    """
                    INSERT OR IGNORE INTO surface_forms (lexeme_id, form, source)
                    VALUES (?, ?, ?)
                    """,
                    (lexeme_id, normalized_surface, "manual"),
                )

                surface_updates: list[str] = []
                surface_params: list[str | int] = []
                if "surface_pos_tag" in normalized_changes:
                    surface_updates.append("pos_tag = ?")
                    surface_params.append(normalized_changes["surface_pos_tag"])
                    applied_fields.append("surface_pos_tag")
                if "surface_morphology" in normalized_changes:
                    surface_updates.append("morphology = ?")
                    surface_params.append(normalized_changes["surface_morphology"])
                    applied_fields.append("surface_morphology")
                if "surface_translation" in normalized_changes:
                    surface_updates.append("english_translation = ?")
                    surface_updates.append("translation_provider = ?")
                    surface_params.append(normalized_changes["surface_translation"])
                    surface_params.append(provider_name)
                    applied_fields.append("surface_translation")

                if surface_updates:
                    conn.execute(
                        f"""
                        UPDATE surface_forms
                        SET {", ".join(surface_updates)}
                        WHERE lexeme_id = ? AND form = ?
                        """,
                        (*surface_params, lexeme_id, normalized_surface),
                    )

        self._invalidate_pos_cache(normalized_lemma, normalized_surface)
        if applied_fields and provider_name == "gemini":
            self._append_gemini_change_log(
                {
                    "timestamp_utc": datetime.now(UTC).isoformat(),
                    "provider": provider_name,
                    "stored_lemma": normalized_lemma,
                    "stored_surface_form": normalized_surface,
                    "applied_fields": applied_fields,
                    "suggested_changes": {
                        key: normalized_changes[key]
                        for key in accepted_fields
                        if key in normalized_changes
                    },
                    "before": {
                        "lexeme": lexeme_before,
                        "surface": surface_before,
                    },
                }
            )

        return ApplyVerificationChangesResponse(
            status="applied" if applied_fields else "skipped",
            stored_lemma=normalized_lemma,
            stored_surface_form=normalized_surface,
            applied_fields=applied_fields,
        )

    def generate_translation(self, surface_token: str, lemma_candidate: str | None) -> GenerateTranslationResponse:
        normalized_surface = normalize_token(surface_token)
        normalized_lemma = normalize_token(lemma_candidate or "")
        stored_lemma = normalized_lemma or normalized_surface

        if not normalized_surface:
            raise ValueError("surface_token or lemma_candidate is required")

        english_translation = self._lookup_translation(normalized_surface)
        provider = self._translation_provider_name()
        if english_translation:
            with get_connection(self._db_path) as conn:
                conn.execute(
                    """
                    UPDATE surface_forms
                    SET english_translation = ?, translation_provider = ?
                    WHERE form = ?
                    """,
                    (english_translation, provider, normalized_surface),
                )

        return GenerateTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_word=normalized_surface,
            lemma=stored_lemma,
            english_translation=english_translation,
        )


    def resolve_query(
        self,
        query_text: str,
        *,
        include_translations: bool = True,
        include_language_detection: bool = True,
    ) -> ResolveQueryResponse:
        query_without_comments = strip_inline_comments(query_text)
        normalized_query = normalize_token(query_without_comments)
        if not normalized_query:
            raise ValueError("query_text is required")

        if is_short_letter_word(normalized_query):
            return ResolveQueryResponse(
                query_surface=normalized_query,
                query_lemma=None,
                classification="uncertain",
                matched_lemma=None,
                matched_lemma_summary=None,
                query_pos_tag=None,
                query_morphology=None,
                resolved_surface=normalized_query,
                resolved_lemma=None,
                da_to_en_translation=None,
                en_to_da_translation=None,
                en_to_da_lemma=None,
                en_to_da_pos_tag=None,
                en_to_da_morphology=None,
                query_language=None,
                query_language_confidence=None,
                word_actions=[],
            )

        classifier = LemmaAwareClassifier(
            self._db_path,
            nlp_adapter=self._nlp_adapter,
            typo_engine=self._typo_engine,
        )
        token = classifier.classify(normalized_query)
        query_pos_tag, query_morphology = self._extract_pos_and_morphology(normalized_query)

        matched_lemma_summary: ResolveQueryResponse.MatchedLemmaSummary | None = None
        if token.matched_lemma:
            with get_connection(self._db_path) as conn:
                lemma_row = conn.execute(
                    """
                    SELECT l.lemma, l.english_translation, COUNT(sf.id) AS variation_count
                    FROM lexemes l
                    LEFT JOIN surface_forms sf ON sf.lexeme_id = l.id
                    WHERE l.lemma = ?
                    GROUP BY l.id
                    LIMIT 1
                    """,
                    (token.matched_lemma,),
                ).fetchone()
            if lemma_row is not None:
                matched_lemma_summary = ResolveQueryResponse.MatchedLemmaSummary(
                    lemma=lemma_row["lemma"],
                    english_translation=lemma_row["english_translation"],
                    variation_count=lemma_row["variation_count"],
                )

        resolved_surface = token.normalized_token or normalized_query
        resolved_lemma = token.lemma_candidate
        da_to_en_translation: str | None = None
        en_to_da_translation: str | None = None
        en_to_da_lemma: str | None = None
        en_to_da_pos_tag: str | None = None
        en_to_da_morphology: str | None = None
        query_language: Literal["en", "da", "ambiguous"] | None = None
        query_language_confidence: float | None = None

        if include_translations:
            translated = self._lookup_translation(normalized_query)
            if translated:
                normalized_translation = normalize_token(translated)
                if self._normalize_comparable(normalized_translation) != self._normalize_comparable(normalized_query):
                    da_to_en_translation = normalized_translation

            reverse_translated = self._lookup_reverse_translation(normalized_query)
            if reverse_translated:
                normalized_reverse = normalize_token(reverse_translated)
                if self._normalize_comparable(normalized_reverse) != self._normalize_comparable(normalized_query):
                    en_to_da_translation = normalized_reverse

            if en_to_da_translation:
                en_to_da_pos_tag, en_to_da_morphology = self._extract_pos_and_morphology(en_to_da_translation)
                translated_classification = classifier.classify(en_to_da_translation)
                en_to_da_lemma = translated_classification.matched_lemma or translated_classification.lemma_candidate

        if include_language_detection:
            detected = self.detect_word_language(normalized_query)
            query_language = detected.language
            query_language_confidence = max(0.0, min(1.0, float(detected.confidence)))

        if (
            token.match_source == "none"
            and en_to_da_translation
            and (
                query_language == "en"
                or (query_language != "da" and self._is_likely_english_word(normalized_query))
                or not resolved_lemma
                or self._normalize_comparable(resolved_lemma) == self._normalize_comparable(normalized_query)
            )
        ):
            resolved_surface = en_to_da_translation
            resolved_lemma = en_to_da_translation

        word_actions = build_word_action_suggestions(
            classification=token.classification,
            query_surface=token.normalized_token or normalized_query,
            query_lemma=token.lemma_candidate,
            query_pos_tag=query_pos_tag,
            query_morphology=query_morphology,
            matched_lemma=token.matched_lemma,
            da_to_en_translation=da_to_en_translation,
            en_to_da_translation=en_to_da_translation,
            en_to_da_lemma=en_to_da_lemma,
            en_to_da_pos_tag=en_to_da_pos_tag,
            en_to_da_morphology=en_to_da_morphology,
            query_language=query_language,
            query_language_confidence=query_language_confidence,
        )

        return ResolveQueryResponse(
            query_surface=token.normalized_token or normalized_query,
            query_lemma=token.lemma_candidate,
            classification=token.classification,
            matched_lemma=token.matched_lemma,
            matched_lemma_summary=matched_lemma_summary,
            query_pos_tag=query_pos_tag,
            query_morphology=query_morphology,
            resolved_surface=resolved_surface,
            resolved_lemma=resolved_lemma,
            da_to_en_translation=da_to_en_translation,
            en_to_da_translation=en_to_da_translation,
            en_to_da_lemma=en_to_da_lemma,
            en_to_da_pos_tag=en_to_da_pos_tag,
            en_to_da_morphology=en_to_da_morphology,
            query_language=query_language,
            query_language_confidence=query_language_confidence,
            word_actions=word_actions,
        )

    def generate_phrase_translation(self, source_text: str) -> GeneratePhraseTranslationResponse:
        normalized_source_text = normalize_token(source_text)
        if not normalized_source_text:
            raise ValueError("source_text is required")

        with get_connection(self._db_path) as conn:
            existing = conn.execute(
                """
                SELECT english_translation
                FROM phrase_translations
                WHERE source_phrase = ?
                LIMIT 1
                """,
                (normalized_source_text,),
            ).fetchone()

            if existing is not None:
                cached_translation = existing["english_translation"]
                return GeneratePhraseTranslationResponse(
                    status="cached" if cached_translation else "unavailable",
                    source_text=normalized_source_text,
                    english_translation=cached_translation,
                )

            english_translation = self._lookup_translation(normalized_source_text)
            provider = self._translation_provider_name()
            conn.execute(
                """
                INSERT INTO phrase_translations (
                    source_phrase,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?)
                """,
                (
                    normalized_source_text,
                    english_translation,
                    provider if english_translation else None,
                ),
            )

        return GeneratePhraseTranslationResponse(
            status="generated" if english_translation else "unavailable",
            source_text=normalized_source_text,
            english_translation=english_translation,
        )

    def generate_reverse_translation(self, source_word: str) -> GenerateReverseTranslationResponse:
        normalized_source = normalize_token(source_word)
        if not normalized_source:
            raise ValueError("source_word is required")
        danish_translation_raw = self._lookup_reverse_translation(normalized_source)
        danish_translation = normalize_token(danish_translation_raw) if danish_translation_raw else None
        return GenerateReverseTranslationResponse(
            status="generated" if danish_translation else "unavailable",
            source_word=normalized_source,
            danish_translation=danish_translation,
        )

    def detect_word_language(self, source_word: str) -> DetectWordLanguageResponse:
        normalized_source = normalize_token(source_word)
        if not normalized_source:
            raise ValueError("source_word is required")

        normalized_lower = normalized_source.lower()
        if any(char in normalized_lower for char in ("æ", "ø", "å")):
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="da",
                confidence=0.99,
            )

        if " " in normalized_source:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.25,
            )

        if not normalized_lower.isascii() or not normalized_lower.replace("-", "").replace("'", "").isalpha():
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.25,
            )

        detected_source_language = self._lookup_detected_source_language(normalized_source)
        if normalized_lower in self._AMBIGUOUS_SHORT_WORDS:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.4,
            )

        if len(normalized_lower) <= 2:
            if detected_source_language in {"en", "da"}:
                return DetectWordLanguageResponse(
                    source_word=normalized_source,
                    language=detected_source_language,
                    confidence=0.45,
                )
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="ambiguous",
                confidence=0.4,
            )

        if detected_source_language in {"en", "da"}:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language=detected_source_language,
                confidence=0.82,
            )

        fallback_english_like = bool(
            normalized_lower
            and normalized_lower[0].isalpha()
            and any(char in "aeiouy" for char in normalized_lower)
        )
        if fallback_english_like:
            return DetectWordLanguageResponse(
                source_word=normalized_source,
                language="en",
                confidence=0.55,
            )

        return DetectWordLanguageResponse(
            source_word=normalized_source,
            language="ambiguous",
            confidence=0.35,
        )

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
                SELECT
                    l.lemma AS lemma,
                    l.english_translation AS english_translation,
                    l.pos_tag AS pos_tag,
                    COUNT(sf_all.id) AS variation_count,
                    MIN(sf_match.form) AS match_surface,
                    MAX(
                        CASE
                            WHEN sf_match.form LIKE ? COLLATE NOCASE THEN 1
                            ELSE 0
                        END
                    ) AS has_surface_prefix_match
                FROM lexemes l
                LEFT JOIN surface_forms sf_all ON sf_all.lexeme_id = l.id
                LEFT JOIN surface_forms sf_match
                    ON sf_match.lexeme_id = l.id
                    AND sf_match.form LIKE ? COLLATE NOCASE
                WHERE
                    l.lemma LIKE ? COLLATE NOCASE
                    OR COALESCE(l.english_translation, '') LIKE ? COLLATE NOCASE
                    OR sf_match.id IS NOT NULL
                GROUP BY l.id
                ORDER BY
                    CASE
                        WHEN l.lemma = ? COLLATE NOCASE THEN 0
                        WHEN l.lemma LIKE ? COLLATE NOCASE THEN 1
                        WHEN has_surface_prefix_match = 1 THEN 2
                        WHEN COALESCE(l.english_translation, '') LIKE ? COLLATE NOCASE THEN 3
                        ELSE 4
                    END,
                    l.lemma COLLATE NOCASE
                LIMIT ?
                """,
                (
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
                SELECT
                    id,
                    lemma,
                    english_translation AS english_translation,
                    pos_tag,
                    morphology
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
            lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(lexeme_row["lemma"])
            self._store_lexeme_metadata(lexeme_row["id"], lemma_pos_tag, lemma_morphology)

        surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = []
        uncached_forms = [row["form"] for row in form_rows if row["pos_tag"] is None and row["morphology"] is None]
        extracted_forms = self._extract_pos_and_morphology_batch(uncached_forms)

        for row in form_rows:
            pos_tag = row["pos_tag"]
            morphology = row["morphology"]
            if pos_tag is None and morphology is None:
                pos_tag, morphology = extracted_forms.get(row["form"], (None, None))
                self._store_surface_form_metadata(lexeme_row["id"], row["form"], pos_tag, morphology)
            surface_forms.append(
                LemmaDetailsResponse.SurfaceFormDetails(
                    form=row["form"],
                    english_translation=row["english_translation"],
                    pos_tag=pos_tag,
                    morphology=morphology,
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

    def get_pronunciation_audio(self, form: str) -> PronunciationAudio:
        normalized_form = normalize_token(form)
        if not normalized_form:
            raise ValueError("form is required")

        with get_connection(self._db_path) as conn:
            row = conn.execute(
                """
                SELECT id, pronunciation_audio, pronunciation_mime_type
                FROM surface_forms
                WHERE form = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (normalized_form,),
            ).fetchone()
            if row is None:
                raise LookupError(f"Pronunciation for '{normalized_form}' was not found")

            audio_bytes = row["pronunciation_audio"]
            if isinstance(audio_bytes, bytes) and audio_bytes:
                mime_type = row["pronunciation_mime_type"]
                normalized_mime = mime_type.strip().lower() if isinstance(mime_type, str) and mime_type.strip() else ""
                if _is_pcm_like_mime(normalized_mime):
                    wav_bytes = _pcm_to_wav_bytes(audio_bytes)
                    conn.execute(
                        """
                        UPDATE surface_forms
                        SET pronunciation_audio = ?, pronunciation_mime_type = ?
                        WHERE id = ?
                        """,
                        (wav_bytes, "audio/wav", int(row["id"])),
                    )
                    return PronunciationAudio(audio_bytes=wav_bytes, mime_type="audio/wav")
                if _looks_like_wav(audio_bytes):
                    if normalized_mime not in {"audio/wav", "audio/x-wav"}:
                        conn.execute(
                            """
                            UPDATE surface_forms
                            SET pronunciation_mime_type = ?
                            WHERE id = ?
                            """,
                            ("audio/wav", int(row["id"])),
                        )
                    return PronunciationAudio(audio_bytes=audio_bytes, mime_type="audio/wav")
                return PronunciationAudio(
                    audio_bytes=audio_bytes,
                    mime_type=mime_type if isinstance(mime_type, str) and mime_type.strip() else "audio/wav",
                )

            generated = self._lookup_pronunciation(normalized_form)
            if generated is None:
                if self._tts_service is None:
                    raise RuntimeError(
                        "Text-to-speech is unavailable: configure DANOTE_TTS_AZURE_API_KEY and DANOTE_TTS_AZURE_REGION."
                    )
                raise LookupError(f"Pronunciation for '{normalized_form}' was not found")
            generated = _normalize_pronunciation_audio(generated)

            conn.execute(
                """
                UPDATE surface_forms
                SET pronunciation_audio = ?,
                    pronunciation_mime_type = ?,
                    pronunciation_provider = ?,
                    pronunciation_model = ?,
                    pronunciation_generated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    generated.audio_bytes,
                    generated.mime_type,
                    self._tts_provider_name(),
                    self._tts_model_name(),
                    int(row["id"]),
                ),
            )
            return generated



    def _normalize_comparable(self, value: str) -> str:
        return " ".join(value.strip().lower().split())

    def _is_likely_english_word(self, value: str) -> bool:
        normalized = value.strip().lower()
        if not normalized or " " in normalized:
            return False
        if any(char in normalized for char in ("æ", "ø", "å")):
            return False
        allowed = set("abcdefghijklmnopqrstuvwxyz'-")
        if any(char not in allowed for char in normalized):
            return False
        return any(char in "aeiouy" for char in normalized)

    def _extract_pos_and_morphology_batch(self, values: list[str]) -> dict[str, tuple[str | None, str | None]]:
        return {value: self._extract_pos_and_morphology(value) for value in values}

    def _extract_pos_and_morphology(self, value: str) -> tuple[str | None, str | None]:
        cached = self._pos_morph_cache.get(value)
        if cached is not None:
            return cached

        if self._nlp_adapter is None:
            self._pos_morph_cache[value] = (None, None)
            return None, None

        for token in self._nlp_adapter.tokenize(value):
            surface = token.text
            if not surface.strip():
                continue
            if token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            extracted = (token.pos, token.morphology)
            self._pos_morph_cache[value] = extracted
            return extracted

        self._pos_morph_cache[value] = (None, None)
        return None, None


    def _lookup_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None

        try:
            translated = self._translation_service.translate_da_to_en(source_word)
            return self._normalize_translation_value(translated)
        except Exception:
            return None

    def _lookup_reverse_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None

        translate_en_to_da = getattr(self._translation_service, "translate_en_to_da", None)
        if not callable(translate_en_to_da):
            return None

        try:
            translated = translate_en_to_da(source_word)
            return self._normalize_translation_value(translated)
        except Exception:
            return None

    def _lookup_detected_source_language(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None

        detect_source_language = getattr(self._translation_service, "detect_source_language", None)
        if not callable(detect_source_language):
            return None

        try:
            provider_language = detect_source_language(source_word)
        except Exception:
            return None

        if not provider_language:
            return None

        normalized = provider_language.strip().lower()
        if normalized.startswith("en"):
            return "en"
        if normalized.startswith("da"):
            return "da"
        return None

    def _translation_provider_name(self) -> str:
        provider = getattr(self._translation_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "translation"

    def _lookup_pronunciation(self, source_word: str) -> PronunciationAudio | None:
        if self._tts_service is None:
            return None

        synthesize = getattr(self._tts_service, "synthesize", None)
        if not callable(synthesize):
            return None

        try:
            return synthesize(source_word)
        except Exception:
            return None

    def _tts_provider_name(self) -> str:
        provider = getattr(self._tts_service, "provider", None)
        if isinstance(provider, str):
            cleaned = provider.strip().lower()
            if cleaned:
                return cleaned
        return "tts"

    def _tts_model_name(self) -> str | None:
        model = getattr(self._tts_service, "model", None)
        if isinstance(model, str):
            cleaned = model.strip()
            if cleaned:
                return cleaned
        return None

    def _display_lemma_for_list(self, lemma: str, pos_tag: str | None) -> str:
        if pos_tag is None:
            pos_tag, _morphology = self._extract_pos_and_morphology(lemma)
        if pos_tag in {"VERB", "AUX"}:
            return f"at {lemma}"
        return lemma

    @staticmethod
    def _normalize_translation_value(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            return None
        return cleaned.lower()

    def _append_gemini_change_log(self, payload: dict[str, object]) -> None:
        if self._gemini_changes_log_path is None:
            return
        try:
            self._gemini_changes_log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._gemini_changes_log_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(payload, ensure_ascii=True, sort_keys=True))
                handle.write("\n")
        except Exception:
            logger.exception(
                "wordbank_gemini_change_log_write_failed",
                extra={"gemini_changes_log_path": str(self._gemini_changes_log_path)},
            )

    def _ensure_surface_pronunciation(
        self,
        *,
        conn: sqlite3.Connection,
        lexeme_id: int,
        form: str,
        force: bool = False,
    ) -> bool:
        existing = conn.execute(
            """
            SELECT id, pronunciation_audio
            FROM surface_forms
            WHERE lexeme_id = ? AND form = ?
            LIMIT 1
            """,
            (lexeme_id, form),
        ).fetchone()

        existing_audio = existing["pronunciation_audio"] if existing is not None else None
        if not force and isinstance(existing_audio, bytes) and existing_audio:
            return False

        generated = self._lookup_pronunciation(form)
        if generated is None:
            return False
        generated = _normalize_pronunciation_audio(generated)

        if existing is None:
            conn.execute(
                """
                INSERT INTO surface_forms (
                    lexeme_id,
                    form,
                    source,
                    pronunciation_audio,
                    pronunciation_mime_type,
                    pronunciation_provider,
                    pronunciation_model,
                    pronunciation_generated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (
                    lexeme_id,
                    form,
                    "manual",
                    generated.audio_bytes,
                    generated.mime_type,
                    self._tts_provider_name(),
                    self._tts_model_name(),
                ),
            )
            return True

        conn.execute(
            """
            UPDATE surface_forms
            SET pronunciation_audio = ?,
                pronunciation_mime_type = ?,
                pronunciation_provider = ?,
                pronunciation_model = ?,
                pronunciation_generated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                generated.audio_bytes,
                generated.mime_type,
                self._tts_provider_name(),
                self._tts_model_name(),
                int(existing["id"]),
            ),
        )
        return True

    def _invalidate_pos_cache(self, lemma: str, surface: str | None) -> None:
        self._pos_morph_cache.pop(lemma, None)
        if surface:
            self._pos_morph_cache.pop(surface, None)

    def _store_lexeme_metadata(self, lexeme_id: int, pos_tag: str | None, morphology: str | None) -> None:
        with get_connection(self._db_path) as conn:
            conn.execute(
                """
                UPDATE lexemes
                SET pos_tag = ?, morphology = ?
                WHERE id = ?
                """,
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
                """
                UPDATE surface_forms
                SET pos_tag = ?, morphology = ?
                WHERE lexeme_id = ? AND form = ?
                """,
                (pos_tag, morphology, lexeme_id, form),
            )

    def _queued_verification_result(self) -> AddWordResponse.VerificationResult:
        if self._verification_service is None:
            return AddWordResponse.VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )

        provider_name, reviewer_name = self._verification_metadata()
        return AddWordResponse.VerificationResult(
            status="queued",
            provider=provider_name,
            reviewer_role=reviewer_name,
            message="Word verification queued.",
            composed_word_count=None,
        )

    def _verification_metadata(self) -> tuple[str, str | None]:
        provider = getattr(self._verification_service, "provider", None)
        reviewer_role = getattr(self._verification_service, "reviewer_role", None)
        provider_name = provider.strip().lower() if isinstance(provider, str) and provider.strip() else "verification"
        reviewer_name = reviewer_role.strip() if isinstance(reviewer_role, str) and reviewer_role.strip() else None
        return provider_name, reviewer_name

    def _build_verification_input(
        self,
        *,
        stored_lemma: str,
        stored_surface_form: str | None,
    ) -> WordVerificationInput:
        lexeme_source = "manual"
        lexeme_translation: str | None = None
        lexeme_translation_provider: str | None = None
        surface_source: str | None = None
        surface_translation: str | None = None
        surface_translation_provider: str | None = None

        with get_connection(self._db_path) as conn:
            lexeme_row = conn.execute(
                """
                SELECT id, source, english_translation, translation_provider
                FROM lexemes
                WHERE lemma = ?
                LIMIT 1
                """,
                (stored_lemma,),
            ).fetchone()

            if lexeme_row is not None:
                lexeme_source = lexeme_row["source"]
                lexeme_translation = lexeme_row["english_translation"]
                lexeme_translation_provider = lexeme_row["translation_provider"]

                if stored_surface_form:
                    surface_row = conn.execute(
                        """
                        SELECT source, english_translation, translation_provider
                        FROM surface_forms
                        WHERE lexeme_id = ? AND form = ?
                        LIMIT 1
                        """,
                        (lexeme_row["id"], stored_surface_form),
                    ).fetchone()
                    if surface_row is not None:
                        surface_source = surface_row["source"]
                        surface_translation = surface_row["english_translation"]
                        surface_translation_provider = surface_row["translation_provider"]

        lemma_pos_tag, lemma_morphology = self._extract_pos_and_morphology(stored_lemma)
        surface_pos_tag: str | None = None
        surface_morphology: str | None = None
        if stored_surface_form:
            surface_pos_tag, surface_morphology = self._extract_pos_and_morphology(stored_surface_form)

        return WordVerificationInput(
            stored_lemma=stored_lemma,
            stored_surface_form=stored_surface_form,
            lexeme_source=lexeme_source,
            lexeme_translation=lexeme_translation,
            lexeme_translation_provider=lexeme_translation_provider,
            surface_source=surface_source,
            surface_translation=surface_translation,
            surface_translation_provider=surface_translation_provider,
            lemma_pos_tag=lemma_pos_tag,
            lemma_morphology=lemma_morphology,
            surface_pos_tag=surface_pos_tag,
            surface_morphology=surface_morphology,
        )

    def _verify_added_word(self, payload: WordVerificationInput) -> AddWordResponse.VerificationResult:
        if self._verification_service is None:
            return AddWordResponse.VerificationResult(
                status="skipped",
                provider=None,
                reviewer_role=None,
                message="Word verification is disabled.",
            )

        provider_name, reviewer_name = self._verification_metadata()

        try:
            verdict = self._verification_service.verify_word_entry(payload)
        except Exception as exc:
            return AddWordResponse.VerificationResult(
                status="error",
                provider=provider_name,
                reviewer_role=reviewer_name,
                message=f"Verification task failed: {exc}",
                composed_word_count=None,
                problem=str(exc),
                change_to_implement=(
                    "Fix Gemini verification setup or provider errors, then run verification again."
                ),
                suggested_changes=None,
            )

        return AddWordResponse.VerificationResult(
            status=verdict.verdict,
            provider=provider_name,
            reviewer_role=reviewer_name,
            message=verdict.message,
            composed_word_count=getattr(verdict, "composed_word_count", None),
            problem=getattr(verdict, "problem", None),
            change_to_implement=getattr(verdict, "change_to_implement", None),
            suggested_changes=getattr(verdict, "suggested_changes", None),
        )

    def reset_database(self) -> ResetDatabaseResponse:
        if self._db_path.exists():
            os.remove(self._db_path)
        apply_migrations(self._db_path)
        if self._typo_engine is not None:
            self._typo_engine.invalidate_cache()

        return ResetDatabaseResponse(
            status="reset",
            message="Database reset complete.",
        )

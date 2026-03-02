from __future__ import annotations

import os
from typing import Literal

from app.api.schemas.v1.wordbank import (
    AddWordResponse,
    DetectWordLanguageResponse,
    GeneratePhraseTranslationResponse,
    GenerateReverseTranslationResponse,
    GenerateTranslationResponse,
    LemmaDetailsResponse,
    LemmaListResponse,
    LemmaSummary,
    ResetDatabaseResponse,
    ResolveQueryResponse,
    VerifyWordResponse,
    WordActionSuggestion,
)
from app.db.migrations import apply_migrations, get_connection
from app.nlp.adapter import NLPAdapter
from app.nlp.token_filter import is_short_letter_word, is_wordlike_token
from app.services.text_preprocessing import strip_inline_comments
from app.services.token_classifier import LemmaAwareClassifier, normalize_token
from app.services.translation import TranslationService
from app.services.verification import WordVerificationInput, WordVerificationService


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
    ):
        self._db_path = db_path
        self._typo_engine = typo_engine
        self._translation_service = translation_service
        self._nlp_adapter = nlp_adapter
        self._verification_service = verification_service
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
                    morphology
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
                )
            )

        return LemmaDetailsResponse(
            lemma=lexeme_row["lemma"],
            english_translation=lexeme_row["english_translation"],
            pos_tag=lemma_pos_tag,
            morphology=lemma_morphology,
            surface_forms=surface_forms,
        )



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
            return self._translation_service.translate_da_to_en(source_word)
        except Exception:
            return None

    def _lookup_reverse_translation(self, source_word: str) -> str | None:
        if self._translation_service is None:
            return None

        translate_en_to_da = getattr(self._translation_service, "translate_en_to_da", None)
        if not callable(translate_en_to_da):
            return None

        try:
            return translate_en_to_da(source_word)
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

    def _display_lemma_for_list(self, lemma: str, pos_tag: str | None) -> str:
        if pos_tag is None:
            pos_tag, _morphology = self._extract_pos_and_morphology(lemma)
        if pos_tag in {"VERB", "AUX"}:
            return f"at {lemma}"
        return lemma

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
            )

        return AddWordResponse.VerificationResult(
            status=verdict.verdict,
            provider=provider_name,
            reviewer_role=reviewer_name,
            message=verdict.message,
            composed_word_count=getattr(verdict, "composed_word_count", None),
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

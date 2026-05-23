from __future__ import annotations

import difflib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Literal, Protocol

from app.services.gemini_translation_helpers import is_retryable_exception


class SentenceVerificationError(RuntimeError):
    """Raised when Gemini sentence verification cannot complete."""


@dataclass(frozen=True, slots=True)
class SentenceVerificationErrorSpan:
    start: int    # char offset, inclusive
    end: int      # char offset, exclusive
    message: str


@dataclass(frozen=True, slots=True)
class SentenceMWESpan:
    start: int
    end: int
    surface: str
    lemma: str
    pos_tag: str | None = None
    gloss: str | None = None
    english_translation: str | None = None


@dataclass(frozen=True, slots=True)
class SentenceVerificationResult:
    is_valid: bool
    errors: list[SentenceVerificationErrorSpan]
    corrected_text: str | None
    language: Literal["da", "en", "unknown"]
    is_multi_word_expression: bool = False
    mwe_lemma: str | None = None
    mwe_pos_tag: str | None = None
    mwe_gloss: str | None = None
    mwe_english_translation: str | None = None
    mwe_spans: list[SentenceMWESpan] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _WordSpan:
    start: int
    end: int
    text: str


class SentenceVerificationService(Protocol):
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult: ...


def _build_prompt(source_text: str) -> str:
    return (
        "You are a Danish language expert.\n"
        f'Check this text for typos and grammatical errors: "{source_text}"\n\n'
        "Additionally, detect any Multi-Word Expressions (MWEs) present in the text.\n"
        "Multi-Word Expressions are combinations of words that act as a single semantic unit, including:\n"
        "- Danish phrasal verbs or verb-particle constructions (e.g., 'se efter', 'kigge efter', 'slukke for', 'tage af sted')\n"
        "- Fixed idiomatic expressions (e.g., 'skyde papegøjen', 'bide i det sure æble')\n"
        "Do NOT classify regular noun phrases, free word combinations (e.g., 'spise æble'), or separable verbs acting compositional as MWEs.\n\n"
        "Return JSON only:\n"
        '- "is_valid": true if no errors, false otherwise\n'
        '- "errors": array of {start, end, message} with 0-indexed char offsets for each error; empty if valid\n'
        '- "corrected_text": fully corrected sentence string if is_valid is false, null if is_valid is true\n'
        '- "language": "da" if Danish, "en" if English, "unknown" otherwise\n'
        '- "is_multi_word_expression": true if the ENTIRE input is exactly one multi-word expression (e.g. "se efter"), false otherwise\n'
        '- "mwe_lemma": the canonical infinitive/dictionary form of the MWE if the entire input is an MWE, null otherwise (e.g., "se efter" if input is "ser efter")\n'
        '- "mwe_pos_tag": the syntactic part-of-speech of the MWE using STANDARD Universal Dependencies tags ("VERB" for phrasal verbs/verbal idioms, "NOUN" for nominal idioms, "ADJ", "ADV", etc.). Do NOT use "phrasal_verb" or "idiom" — return the underlying syntactic role. Null if the entire input is not an MWE.\n'
        '- "mwe_gloss": a brief Danish explanation/gloss of the MWE if the entire input is an MWE, null otherwise\n'
        '- "mwe_english_translation": English translation of the MWE if the entire input is an MWE, null otherwise\n'
        '- "mwe_spans": list of MWE spans detected within the sentence if the input is a sentence. Each span has the fields:\n'
        '  - "start": 0-indexed character offset of the start of the MWE span (inclusive)\n'
        '  - "end": 0-indexed character offset of the end of the MWE span (exclusive)\n'
        '  - "surface": the exact substring of the MWE in the sentence (e.g. "kigger efter")\n'
        '  - "lemma": the canonical dictionary form (e.g. "se efter")\n'
        '  - "pos_tag": STANDARD Universal Dependencies POS tag ("VERB" for phrasal verbs/verbal idioms, "NOUN" for nominal idioms, "ADJ", "ADV", etc.). Do NOT use "phrasal_verb" or "idiom".\n'
        '  - "gloss": Danish gloss/definition of this expression\n'
        '  - "english_translation": English translation of this expression\n\n'
        "Keep the same capitalization style at the start of the sentence as the source text.\n"
        "Do not flag sentence-initial capitalization by itself as an error.\n"
        "Only correct text that already appears in the source text.\n"
        "Do not add new words, complete unfinished phrases, or autocomplete the sentence.\n"
        "Never add a trailing period to corrected_text unless the source text already ends with a period."
    )


def _preserve_leading_letter_case(source_text: str, corrected_text: str | None) -> str | None:
    if not corrected_text:
        return None

    source_index = next((idx for idx, char in enumerate(source_text) if char.isalpha()), None)
    corrected_index = next((idx for idx, char in enumerate(corrected_text) if char.isalpha()), None)
    if source_index is None or corrected_index is None:
        return corrected_text

    source_char = source_text[source_index]
    corrected_char = corrected_text[corrected_index]
    if source_char.islower() and corrected_char.isupper():
        return (
            corrected_text[:corrected_index]
            + corrected_char.lower()
            + corrected_text[corrected_index + 1:]
        )
    if source_char.isupper() and corrected_char.islower():
        return (
            corrected_text[:corrected_index]
            + corrected_char.upper()
            + corrected_text[corrected_index + 1:]
        )
    return corrected_text


def _preserve_terminal_period_style(source_text: str, corrected_text: str | None) -> str | None:
    if not corrected_text:
        return None

    trimmed_source = source_text.rstrip()
    trimmed_corrected = corrected_text.rstrip()
    if not trimmed_corrected.endswith(".") or trimmed_source.endswith("."):
        return corrected_text

    without_period = trimmed_corrected[:-1].rstrip()
    trailing_whitespace = corrected_text[len(trimmed_corrected):]
    return without_period + trailing_whitespace


def _is_ignorable_case_only_error(
    error: SentenceVerificationErrorSpan,
    source_text: str,
    corrected_text: str | None,
) -> bool:
    if not corrected_text:
        return False

    start = max(error.start, 0)
    end = min(error.end, len(source_text), len(corrected_text))
    if start >= end:
        return False

    source_slice = source_text[start:end]
    corrected_slice = corrected_text[start:end]
    if len(source_slice) != len(corrected_slice):
        return False

    return source_slice != corrected_slice and source_slice.casefold() == corrected_slice.casefold()


def _is_word_character(char: str) -> bool:
    return char.isalnum() or char in {"'", "’", "-"}


def _word_spans(text: str) -> list[_WordSpan]:
    spans: list[_WordSpan] = []
    index = 0
    while index < len(text):
        if not _is_word_character(text[index]):
            index += 1
            continue
        start = index
        index += 1
        while index < len(text) and _is_word_character(text[index]):
            index += 1
        spans.append(_WordSpan(start=start, end=index, text=text[start:index]))
    return spans


def _changed_source_word_spans(source_text: str, corrected_text: str | None) -> list[tuple[int, int]]:
    if not corrected_text:
        return []

    source_words = _word_spans(source_text)
    corrected_words = _word_spans(corrected_text)
    if not source_words or not corrected_words:
        return []

    matcher = difflib.SequenceMatcher(
        a=[span.text.casefold() for span in source_words],
        b=[span.text.casefold() for span in corrected_words],
    )
    changed_spans: list[tuple[int, int]] = []
    for tag, source_start_index, source_end_index, _corrected_start, _corrected_end in matcher.get_opcodes():
        if tag != "replace" or source_start_index >= source_end_index:
            continue
        changed_spans.append(
            (
                source_words[source_start_index].start,
                source_words[source_end_index - 1].end,
            )
        )
    return changed_spans


def _compact_word_text(text: str) -> str:
    return "".join(span.text.casefold() for span in _word_spans(text))


def _introduces_new_word_content(source_text: str, corrected_text: str | None) -> bool:
    if not corrected_text:
        return False

    source_words = _word_spans(source_text)
    corrected_words = _word_spans(corrected_text)
    if len(corrected_words) <= len(source_words):
        return False

    return _compact_word_text(source_text) != _compact_word_text(corrected_text)


def _is_autocomplete_only_response(source_text: str, corrected_text: str | None) -> bool:
    if not corrected_text:
        return False

    source_words = _word_spans(source_text)
    corrected_words = _word_spans(corrected_text)
    if not source_words or len(corrected_words) <= len(source_words):
        return False

    source_texts = [span.text.casefold() for span in source_words]
    corrected_prefix = [span.text.casefold() for span in corrected_words[: len(source_words)]]
    return source_texts == corrected_prefix


def _meaningful_text_bounds(source_text: str) -> tuple[int, int] | None:
    start = next((idx for idx, char in enumerate(source_text) if not char.isspace()), None)
    if start is None:
        return None
    end = next(
        (idx for idx in range(len(source_text) - 1, -1, -1) if not source_text[idx].isspace()),
        None,
    )
    if end is None:
        return None
    return start, end + 1


def _covers_meaningful_input(error: SentenceVerificationErrorSpan, source_text: str) -> bool:
    bounds = _meaningful_text_bounds(source_text)
    if bounds is None:
        return False
    start, end = bounds
    return error.start <= start and error.end >= end


def _is_fragment_feedback_message(message: str) -> bool:
    normalized = " ".join(message.strip().casefold().split())
    if not normalized:
        return False

    fragment_markers = (
        "incomplete",
        "unfinished",
        "fragment",
        "not a complete sentence",
        "not a full sentence",
        "sentence fragment",
        "ufuldstændig",
        "ufuldendt",
        "sætningsfragment",
        "ikke en fuld sætning",
        "ikke en komplet sætning",
    )
    return any(marker in normalized for marker in fragment_markers)


def _should_ignore_fragment_only_feedback(
    source_text: str,
    corrected_text: str | None,
    errors: list[SentenceVerificationErrorSpan],
) -> bool:
    if corrected_text and corrected_text.casefold() != source_text.casefold():
        return False
    if not errors:
        return False
    if source_text.rstrip().endswith((".", "!", "?")):
        return False

    return all(
        _covers_meaningful_input(error, source_text) and _is_fragment_feedback_message(error.message)
        for error in errors
    )


def _normalize_error_spans(
    errors: list[SentenceVerificationErrorSpan],
    source_text: str,
    corrected_text: str | None,
) -> list[SentenceVerificationErrorSpan]:
    if not errors or not corrected_text:
        return errors

    changed_word_spans = _changed_source_word_spans(source_text, corrected_text)
    if not changed_word_spans:
        return errors

    if len(errors) == len(changed_word_spans):
        return [
            SentenceVerificationErrorSpan(
                start=changed_start,
                end=changed_end,
                message=error.message,
            )
            for error, (changed_start, changed_end) in zip(errors, changed_word_spans, strict=False)
        ]

    if len(errors) == 1:
        merged_start = changed_word_spans[0][0]
        merged_end = changed_word_spans[-1][1]
        return [
            SentenceVerificationErrorSpan(
                start=merged_start,
                end=merged_end,
                message=errors[0].message,
            )
        ]

    return errors


_MWE_POS_TAG_ALIASES = {
    "PHRASAL_VERB": "VERB",
    "PHRASALVERB": "VERB",
    "PHRASAL-VERB": "VERB",
    "IDIOM": "VERB",
    "MWE": "VERB",
}


def _normalize_mwe_pos_tag(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped:
        return None
    upper = stripped.upper().replace(" ", "_")
    return _MWE_POS_TAG_ALIASES.get(upper, upper)


def _find_best_substring_match(source_text: str, surface: str, estimated_start: int) -> tuple[int, int] | None:
    surface_stripped = surface.strip()
    if not surface_stripped:
        return None
    surface_len = len(surface_stripped)
    best_start = -1
    best_dist = float("inf")
    
    # Try exact match first
    idx = 0
    while True:
        pos = source_text.find(surface_stripped, idx)
        if pos == -1:
            break
        dist = abs(pos - estimated_start)
        if dist < best_dist:
            best_dist = dist
            best_start = pos
        idx = pos + 1
        
    # Try case-insensitive match
    if best_start == -1:
        source_lower = source_text.lower()
        surface_lower = surface_stripped.lower()
        idx = 0
        while True:
            pos = source_lower.find(surface_lower, idx)
            if pos == -1:
                break
            dist = abs(pos - estimated_start)
            if dist < best_dist:
                best_dist = dist
                best_start = pos
            idx = pos + 1
            
    if best_start != -1:
        return best_start, best_start + surface_len
    return None


def _parse_result(raw: str | None, source_text: str) -> SentenceVerificationResult:
    if not raw:
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
            is_multi_word_expression=False,
            mwe_lemma=None,
            mwe_pos_tag=None,
            mwe_gloss=None,
            mwe_english_translation=None,
            mwe_spans=[],
        )
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language="unknown",
            is_multi_word_expression=False,
            mwe_lemma=None,
            mwe_pos_tag=None,
            mwe_gloss=None,
            mwe_english_translation=None,
            mwe_spans=[],
        )

    is_valid = bool(data.get("is_valid", True))
    raw_language = data.get("language", "unknown")
    language: Literal["da", "en", "unknown"] = raw_language if raw_language in ("da", "en") else "unknown"
    raw_corrected_text = data.get("corrected_text") or None
    corrected_text = _preserve_terminal_period_style(
        source_text,
        _preserve_leading_letter_case(source_text, raw_corrected_text),
    )
    
    raw_is_mwe = bool(data.get("is_multi_word_expression", False))
    raw_mwe_lemma = data.get("mwe_lemma") or None
    raw_mwe_pos_tag = _normalize_mwe_pos_tag(data.get("mwe_pos_tag"))
    raw_mwe_gloss = data.get("mwe_gloss") or None
    raw_mwe_english_translation = data.get("mwe_english_translation") or None

    is_mwe = False
    if raw_is_mwe and raw_mwe_lemma:
        if " " in source_text.strip():
            is_mwe = True

    if not is_mwe:
        raw_mwe_lemma = None
        raw_mwe_pos_tag = None
        raw_mwe_gloss = None
        raw_mwe_english_translation = None

    raw_mwe_spans = data.get("mwe_spans") or []
    mwe_spans: list[SentenceMWESpan] = []
    for span in raw_mwe_spans:
        if not isinstance(span, dict):
            continue
        start = span.get("start")
        end = span.get("end")
        surface = span.get("surface")
        lemma = span.get("lemma")
        if not isinstance(start, int) or not isinstance(end, int) or not isinstance(surface, str) or not isinstance(lemma, str):
            continue
        
        # Align with substring to prevent byte/decomposition offset errors
        matched_bounds = _find_best_substring_match(source_text, surface, start)
        if matched_bounds is not None:
            start, end = matched_bounds
        
        # Guard: check bounds to verify alignment with whitespace-delimited tokens
        if start > 0 and source_text[start - 1].isalnum():
            continue
        if end < len(source_text) and source_text[end].isalnum():
            continue

        mwe_spans.append(SentenceMWESpan(
            start=start,
            end=end,
            surface=source_text[start:end],
            lemma=lemma,
            pos_tag=_normalize_mwe_pos_tag(span.get("pos_tag")),
            gloss=span.get("gloss") or None,
            english_translation=span.get("english_translation") or None,
        ))

    if _is_autocomplete_only_response(source_text, corrected_text):
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language=language,
            is_multi_word_expression=is_mwe,
            mwe_lemma=raw_mwe_lemma,
            mwe_pos_tag=raw_mwe_pos_tag,
            mwe_gloss=raw_mwe_gloss,
            mwe_english_translation=raw_mwe_english_translation,
            mwe_spans=mwe_spans,
        )
    filtered_corrected_reference = raw_corrected_text
    if _introduces_new_word_content(source_text, corrected_text):
        corrected_text = None
        filtered_corrected_reference = None
    raw_errors = data.get("errors") or []
    errors: list[SentenceVerificationErrorSpan] = []
    for e in raw_errors:
        if not isinstance(e, dict):
            continue
        start = e.get("start")
        end = e.get("end")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        errors.append(SentenceVerificationErrorSpan(
            start=start,
            end=end,
            message=str(e.get("message", "")),
        ))
    if _should_ignore_fragment_only_feedback(source_text, corrected_text, errors):
        return SentenceVerificationResult(
            is_valid=True,
            errors=[],
            corrected_text=None,
            language=language,
            is_multi_word_expression=is_mwe,
            mwe_lemma=raw_mwe_lemma,
            mwe_pos_tag=raw_mwe_pos_tag,
            mwe_gloss=raw_mwe_gloss,
            mwe_english_translation=raw_mwe_english_translation,
            mwe_spans=mwe_spans,
        )
    filtered_errors = [
        error for error in errors
        if not _is_ignorable_case_only_error(error, source_text, filtered_corrected_reference)
    ]
    normalized_errors = _normalize_error_spans(filtered_errors, source_text, corrected_text)
    normalized_is_valid = is_valid if normalized_errors else True
    normalized_corrected_text = (
        None
        if (
            corrected_text is None
            or (not normalized_errors and corrected_text.casefold() == source_text.casefold())
        )
        else corrected_text
    )
    return SentenceVerificationResult(
        is_valid=normalized_is_valid,
        errors=normalized_errors,
        corrected_text=normalized_corrected_text,
        language=language,
        is_multi_word_expression=is_mwe,
        mwe_lemma=raw_mwe_lemma,
        mwe_pos_tag=raw_mwe_pos_tag,
        mwe_gloss=raw_mwe_gloss,
        mwe_english_translation=raw_mwe_english_translation,
        mwe_spans=mwe_spans,
    )


@dataclass
class GeminiSentenceVerificationService:
    """Danish sentence grammar/typo checker backed by Gemini."""

    api_key: str
    model: str = "gemini-3.1-flash-lite"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        if not normalized_key:
            raise SentenceVerificationError("Gemini API key is required.")
        if not normalized_model:
            raise SentenceVerificationError("Gemini model is required.")
        self.api_key = normalized_key
        self.model = normalized_model

    def verify_sentence(self, source_text: str) -> SentenceVerificationResult:
        prompt = _build_prompt(source_text)
        raw = self._generate_text(prompt)
        return _parse_result(raw, source_text)

    def close(self) -> None:
        self._client = None

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise SentenceVerificationError("google-genai package required.") from exc
            genai_types = self._genai_types()
            timeout_ms = max(1, math.ceil(self.timeout_seconds * 1000))
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=genai_types.HttpOptions(timeout=timeout_ms),
            )
        return self._client

    def _genai_types(self) -> object:
        try:
            from google.genai import types as genai_types  # type: ignore import-not-found
        except ImportError as exc:
            raise SentenceVerificationError("google-genai package required.") from exc
        return genai_types

    def _response_config(self) -> object:
        genai_types = self._genai_types()
        return genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "OBJECT",
                "properties": {
                    "is_valid": {"type": "BOOLEAN"},
                    "errors": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "start": {"type": "INTEGER"},
                                "end": {"type": "INTEGER"},
                                "message": {"type": "STRING"},
                            },
                            "required": ["start", "end", "message"],
                        },
                    },
                    "corrected_text": {"type": "STRING", "nullable": True},
                    "language": {
                        "type": "STRING",
                        "enum": ["da", "en", "unknown"],
                    },
                    "is_multi_word_expression": {"type": "BOOLEAN"},
                    "mwe_lemma": {"type": "STRING", "nullable": True},
                    "mwe_pos_tag": {"type": "STRING", "nullable": True},
                    "mwe_gloss": {"type": "STRING", "nullable": True},
                    "mwe_english_translation": {"type": "STRING", "nullable": True},
                    "mwe_spans": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "start": {"type": "INTEGER"},
                                "end": {"type": "INTEGER"},
                                "surface": {"type": "STRING"},
                                "lemma": {"type": "STRING"},
                                "pos_tag": {"type": "STRING", "nullable": True},
                                "gloss": {"type": "STRING", "nullable": True},
                                "english_translation": {"type": "STRING", "nullable": True},
                            },
                            "required": ["start", "end", "surface", "lemma"],
                        },
                    },
                },
                "required": [
                    "is_valid",
                    "errors",
                    "corrected_text",
                    "language",
                    "is_multi_word_expression",
                    "mwe_lemma",
                    "mwe_pos_tag",
                    "mwe_gloss",
                    "mwe_english_translation",
                    "mwe_spans",
                ],
            },
            temperature=0,
            max_output_tokens=512,
            thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
        )

    def _generate_text(self, prompt: str) -> str | None:
        response = self._generate_content(prompt, config=self._response_config())
        text = getattr(response, "text", None)
        cleaned = text.strip() if isinstance(text, str) else ""
        return cleaned or None

    def _generate_content(self, prompt: str, *, config: object | None = None) -> object:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                return client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
            except Exception as exc:
                if attempt < self.max_retries and self._is_retryable_exception(exc):
                    delay = self.backoff_seconds * (2 ** attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise SentenceVerificationError(
                    f"Gemini sentence verification failed: {exc}"
                ) from exc
        raise SentenceVerificationError("Gemini sentence verification failed after retries.")

    @staticmethod
    def _is_retryable_exception(exc: Exception) -> bool:
        return is_retryable_exception(
            exc,
            exception_status_code=GeminiSentenceVerificationService._exception_status_code,
        )

    @staticmethod
    def _exception_status_code(exc: Exception) -> int | None:
        for candidate in (exc, getattr(exc, "response", None), getattr(exc, "cause", None)):
            if candidate is None:
                continue
            status_code = getattr(candidate, "status_code", None)
            if isinstance(status_code, int):
                return status_code
            code = getattr(candidate, "code", None)
            if isinstance(code, int):
                return code
        return None

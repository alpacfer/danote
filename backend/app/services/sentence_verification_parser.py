from __future__ import annotations

import difflib
import json
import re
from typing import Literal

from app.services.sentence_verification import (
    SentenceMWEMeaning,
    SentenceMWESpan,
    SentenceVerificationErrorSpan,
    SentenceVerificationResult,
)


class _WordSpan:
    start: int
    end: int
    text: str

    def __init__(self, start: int, end: int, text: str):
        self.start = start
        self.end = end
        self.text = text


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

_DANISH_CHARS = frozenset("æøåÆØÅ")
_DANISH_INFINITIVE_RE = re.compile(r"^at\s+\w", re.IGNORECASE)


def _strip_danish_parenthetical(value: str | None) -> str | None:
    """Remove parenthetical blocks containing Danish text from an English translation.

    Gemini occasionally appends a Danish gloss in parentheses, e.g.:
        "to run away (at flygte eller forlade et sted hurtigt)"

    Detection heuristics (either triggers removal):
      1. The parenthetical contains at least one Danish letter (æ, ø, å).
      2. The parenthetical starts with the Danish infinitive marker "at " and
         contains 4+ words total — a strong signal of a Danish gloss clause.

    Pure-English disambiguators like "(clothes)" or "(figurative)" are left
    intact.
    """
    if not value:
        return None
    def _is_danish_paren(m: re.Match) -> str:  # type: ignore[type-arg]
        inner = m.group(1)
        if any(ch in _DANISH_CHARS for ch in inner):
            return ""
        inner_stripped = inner.strip()
        if _DANISH_INFINITIVE_RE.match(inner_stripped) and len(inner_stripped.split()) >= 4:
            return ""
        return m.group(0)
    cleaned = re.sub(r"\(([^)]+)\)", _is_danish_paren, value)
    return " ".join(cleaned.split()) or None



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


def _parse_mwe_meanings(raw_meanings: object) -> list[SentenceMWEMeaning]:
    if not isinstance(raw_meanings, list):
        return []
    parsed: list[SentenceMWEMeaning] = []
    seen_keys: set[str] = set()
    for item in raw_meanings:
        if not isinstance(item, dict):
            continue
        gloss = item.get("gloss") or None
        english_translation = _strip_danish_parenthetical(item.get("english_translation") or None)
        if not gloss and not english_translation:
            continue
        meaning_key_raw = item.get("meaning_key")
        meaning_key = (
            str(meaning_key_raw).strip().lower()
            if isinstance(meaning_key_raw, str) and meaning_key_raw.strip()
            else None
        )
        dedupe_key = meaning_key or (english_translation or "").strip().lower() or (gloss or "").strip().lower()
        if dedupe_key in seen_keys:
            continue
        seen_keys.add(dedupe_key)
        parsed.append(SentenceMWEMeaning(
            gloss=gloss,
            english_translation=english_translation,
            pos_tag=_normalize_mwe_pos_tag(item.get("pos_tag")),
            meaning_key=meaning_key,
        ))
    return parsed



def parse_sentence_verification_result(raw: str | None, source_text: str) -> SentenceVerificationResult:
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
            mwe_meanings=[],
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
            mwe_meanings=[],
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
    raw_mwe_english_translation = _strip_danish_parenthetical(data.get("mwe_english_translation") or None)
    mwe_meanings = _parse_mwe_meanings(data.get("mwe_meanings"))


    is_mwe = False
    if raw_is_mwe and raw_mwe_lemma:
        lemma_stripped = raw_mwe_lemma.strip()
        words = lemma_stripped.split()
        has_ending_punc = lemma_stripped.endswith((".", "!", "?"))
        if " " in source_text.strip() and 1 < len(words) <= 6 and not has_ending_punc:
            is_mwe = True

    if not is_mwe:
        raw_mwe_lemma = None
        raw_mwe_pos_tag = None
        raw_mwe_gloss = None
        raw_mwe_english_translation = None
        mwe_meanings = []
    else:
        if mwe_meanings:
            first = mwe_meanings[0]
            if not raw_mwe_gloss:
                raw_mwe_gloss = first.gloss
            if not raw_mwe_english_translation:
                raw_mwe_english_translation = first.english_translation
            if not raw_mwe_pos_tag:
                raw_mwe_pos_tag = first.pos_tag
        elif raw_mwe_gloss or raw_mwe_english_translation:
            mwe_meanings = [SentenceMWEMeaning(
                gloss=raw_mwe_gloss,
                english_translation=raw_mwe_english_translation,
                pos_tag=raw_mwe_pos_tag,
                meaning_key=None,
            )]

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

        matched_bounds = _find_best_substring_match(source_text, surface, start)
        if matched_bounds is not None:
            start, end = matched_bounds

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
            mwe_meanings=mwe_meanings,
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
            mwe_meanings=mwe_meanings,
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
        mwe_meanings=mwe_meanings,
        mwe_spans=mwe_spans,
    )

from __future__ import annotations

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
class SentenceMWEMeaning:
    """One distinct sense of a Multi-Word Expression.

    Polysemous phrasal verbs like "tage på" carry multiple meanings (put on
    clothes / gain weight / go somewhere); each row here represents one. The
    frontend renders one search card per meaning, and saving each card creates
    a separate lexeme_meanings row under the same MWE lexeme.
    """
    gloss: str | None = None
    english_translation: str | None = None
    pos_tag: str | None = None
    meaning_key: str | None = None


@dataclass(frozen=True, slots=True)
class SentenceVerificationResult:
    is_valid: bool
    errors: list[SentenceVerificationErrorSpan]
    corrected_text: str | None
    language: Literal["da", "en", "unknown"]
    is_multi_word_expression: bool = False
    mwe_lemma: str | None = None
    # Single-meaning back-compat fields. When the lemma is polysemous, these
    # mirror the FIRST meaning in `mwe_meanings`; callers preferring per-sense
    # behavior should read `mwe_meanings` directly.
    mwe_pos_tag: str | None = None
    mwe_gloss: str | None = None
    mwe_english_translation: str | None = None
    mwe_meanings: list[SentenceMWEMeaning] = field(default_factory=list)
    mwe_spans: list[SentenceMWESpan] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class _WordSpan:
    start: int
    end: int
    text: str


class SentenceVerificationService(Protocol):
    def verify_sentence(self, source_text: str) -> SentenceVerificationResult: ...


def _build_prompt(source_text: str) -> str:
    """Sentence-verification prompt used by BOTH the search/preview path and the save path.

    Latency invariant: this is the *first* Gemini call the user incurs while typing in
    the search box, so its scope is deliberately narrow. It must only do:
      1. typo / grammar check (errors + corrected_text + language)
      2. Multi-Word Expression detection (is_multi_word_expression, mwe_lemma, mwe_spans)

    Do NOT extend this prompt to also produce related-words, paradigm completions,
    full translations, or any other enrichment — those belong in dedicated background
    Gemini calls (see app.services.related_words, verification_*). Each new
    responsibility added here directly slows down search-as-you-type for every user.
    """
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
        '- "mwe_gloss": a brief Danish explanation/gloss of the MWE\'s MOST COMMON meaning if the entire input is an MWE, null otherwise. (Duplicates the first entry of mwe_meanings — kept for back-compat.)\n'
        '- "mwe_english_translation": English translation of the MWE\'s MOST COMMON meaning if the entire input is an MWE, null otherwise. Must be English only — do not include Danish words or parenthetical Danish explanations.\n'
        '- "mwe_meanings": when is_multi_word_expression is true, an array of DISTINCT senses for the lemma, ordered from most common to least. Even monosemous MWEs return a one-element array. Polysemous phrasal verbs like "tage på" (put on / gain weight / go somewhere) must return one entry per distinct sense. Each entry has fields:\n'
        '  - "gloss": brief Danish explanation/gloss of THIS specific sense\n'
        '  - "english_translation": English translation of THIS specific sense (e.g. "to dress" vs "to gain weight"). Must be English only — never include Danish words or parenthetical Danish text.\n'
        '  - "pos_tag": standard UD POS tag for this sense (usually matches mwe_pos_tag)\n'
        '  - "meaning_key": a short stable identifier for this sense, normalized lowercase and unique within the array (e.g. "iføre sig tøj", "tage til vægt", "tage afsted")\n'
        '  Empty array if not an MWE. Cap at 6 entries — only return clearly distinct, commonly-used senses; do not invent rare meanings.\n'
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
        from app.services.sentence_verification_parser import parse_sentence_verification_result
        prompt = _build_prompt(source_text)
        raw = self._generate_text(prompt)
        return parse_sentence_verification_result(raw, source_text)

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
                    "mwe_meanings": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "gloss": {"type": "STRING", "nullable": True},
                                "english_translation": {"type": "STRING", "nullable": True},
                                "pos_tag": {"type": "STRING", "nullable": True},
                                "meaning_key": {"type": "STRING", "nullable": True},
                            },
                        },
                    },
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
                    "mwe_meanings",
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

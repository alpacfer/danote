from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Literal, Protocol


class VerificationError(RuntimeError):
    """Raised when verification cannot be completed by the provider."""


@dataclass(frozen=True)
class WordVerificationInput:
    stored_lemma: str
    stored_surface_form: str | None
    lexeme_source: str
    lexeme_translation: str | None
    lexeme_translation_provider: str | None
    surface_source: str | None
    lemma_pos_tag: str | None
    lemma_morphology: str | None
    surface_pos_tag: str | None
    surface_morphology: str | None


@dataclass(frozen=True)
class WordVerificationResult:
    verdict: Literal["verified", "flagged"]
    message: str
    composed_word_count: int | None = None
    problem: str | None = None
    change_to_implement: str | None = None
    suggested_changes: dict[str, str | None] | None = None


class WordVerificationService(Protocol):
    provider: str
    reviewer_role: str

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult: ...


@dataclass
class GeminiWordVerificationService:
    """Wordbank entry verifier backed by Gemini Flash."""

    api_key: str
    model: str = "gemini-3-flash-preview"
    timeout_seconds: float = 20.0
    max_retries: int = 2
    backoff_seconds: float = 0.5
    provider: str = field(default="gemini", init=False)
    reviewer_role: str = field(default="Professional Danish Language Expert", init=False)
    _client: object | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        normalized_key = self.api_key.strip()
        normalized_model = self.model.strip()
        if not normalized_key:
            raise VerificationError("Gemini API key is required for word verification.")
        if not normalized_model:
            raise VerificationError("Gemini model is required for word verification.")
        self.api_key = normalized_key
        self.model = normalized_model

    def _ensure_client(self) -> object:
        if self._client is None:
            try:
                from google import genai  # type: ignore import-not-found
            except ImportError as exc:
                raise VerificationError("google-genai package is required for Gemini verification.") from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def close(self) -> None:
        # google-genai does not require explicit close for default client transport.
        self._client = None

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult:
        prompt = self._verification_prompt(payload)
        fallback_word_count = self._infer_word_count(payload)
        raw = self._generate_text(prompt)
        if not raw:
            return WordVerificationResult(
                verdict="flagged",
                message="no_judgment",
                composed_word_count=fallback_word_count,
            )

        parsed = self._parse_response(raw)
        verdict = parsed.get("verdict")
        word_count_raw = parsed.get("word_count")
        word_count = int(word_count_raw) if isinstance(word_count_raw, int) else fallback_word_count
        problem = parsed.get("problem") if isinstance(parsed.get("problem"), str) else None
        change_to_implement = (
            parsed.get("change_to_implement") if isinstance(parsed.get("change_to_implement"), str) else None
        )
        suggested_changes_raw = parsed.get("suggested_changes")
        suggested_changes = (
            suggested_changes_raw
            if isinstance(suggested_changes_raw, dict)
            else None
        )

        if verdict == "incorrect":
            return WordVerificationResult(
                verdict="flagged",
                message="incorrect",
                composed_word_count=word_count,
                problem=problem or "Gemini flagged lexical inconsistency in lemma/surface/POS/morphology/translation.",
                change_to_implement=(
                    change_to_implement
                    or "Update the stored entry so lemma, surface form, POS, morphology, and translations are coherent."
                ),
                suggested_changes=suggested_changes,
            )
        return WordVerificationResult(verdict="verified", message="OK", composed_word_count=word_count)

    def _verification_prompt(self, payload: WordVerificationInput) -> str:
        entry = {
            "where": {
                "lexemes": {
                    "lemma": payload.stored_lemma,
                    "source": payload.lexeme_source,
                    "english_translation": payload.lexeme_translation,
                    "translation_provider": payload.lexeme_translation_provider,
                    "pos_tag": payload.lemma_pos_tag,
                    "morphology": payload.lemma_morphology,
                },
                "surface_forms": {
                    "form": payload.stored_surface_form,
                    "source": payload.surface_source,
                    "pos_tag": payload.surface_pos_tag,
                    "morphology": payload.surface_morphology,
                },
            }
        }
        return (
            "You are a Professional Danish Language Expert.\n"
            "Verify lexical correctness: lemma/surface/POS/morphology/translation coherence.\n"
            "Also count if entry is composed of multiple words (e.g. 'lege plads' -> 2).\n"
            "JSON only:\n"
            "{"
            '"verdict":"correct|incorrect",'
            '"word_count":0,'
            '"problem":"...",'
            '"change_to_implement":"...",'
            '"suggested_changes":{"lemma_pos_tag":null,"lemma_morphology":null,"surface_pos_tag":null,'
            '"surface_morphology":null,"lexeme_translation":null}'
            "}\n"
            "Rules:\n"
            "- If verdict=correct, keep problem/change_to_implement null and suggested_changes as {}.\n"
            "- If verdict=incorrect, provide concrete change instructions and only include changed fields in suggested_changes.\n"
            f"Entry:\n{json.dumps(entry, ensure_ascii=False)}"
        )

    def _parse_response(self, raw: str) -> dict[str, object]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```").strip()
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3].strip()

        try:
            parsed = json.loads(cleaned)
        except ValueError:
            normalized = cleaned.lower()
            if "incorrect" in normalized or "error" in normalized or "mismatch" in normalized:
                return {"verdict": "incorrect", "word_count": None}
            return {"verdict": "correct", "word_count": None}

        if not isinstance(parsed, dict):
            return {"verdict": "incorrect", "word_count": None}

        verdict_value = parsed.get("verdict")
        word_count_value = parsed.get("word_count")
        verdict = verdict_value.strip().lower() if isinstance(verdict_value, str) else "incorrect"
        if verdict not in {"correct", "incorrect"}:
            verdict = "incorrect"
        word_count = word_count_value if isinstance(word_count_value, int) and word_count_value > 0 else None
        out: dict[str, object] = {"verdict": verdict, "word_count": word_count}
        if isinstance(parsed.get("problem"), str):
            out["problem"] = parsed["problem"]
        if isinstance(parsed.get("change_to_implement"), str):
            out["change_to_implement"] = parsed["change_to_implement"]
        suggested_changes_raw = parsed.get("suggested_changes")
        if isinstance(suggested_changes_raw, dict):
            normalized_changes: dict[str, str | None] = {}
            for key in (
                "lemma_pos_tag",
                "lemma_morphology",
                "surface_pos_tag",
                "surface_morphology",
                "lexeme_translation",
            ):
                value = suggested_changes_raw.get(key)
                if value is None or isinstance(value, str):
                    normalized_changes[key] = value
            out["suggested_changes"] = normalized_changes
        return out

    def _infer_word_count(self, payload: WordVerificationInput) -> int:
        source_text = payload.stored_surface_form or payload.stored_lemma
        parts = [part for part in source_text.split() if part]
        return max(1, len(parts))

    def _generate_text(self, prompt: str) -> str | None:
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                client = self._ensure_client()
                response = client.models.generate_content(model=self.model, contents=prompt)
                text = getattr(response, "text", None)
                cleaned = text.strip() if isinstance(text, str) else ""
                return cleaned or None
            except Exception as exc:
                if attempt < self.max_retries:
                    delay = self.backoff_seconds * (2**attempt)
                    if delay > 0:
                        time.sleep(delay)
                    continue
                raise VerificationError(f"Gemini verification request failed: {exc}") from exc
        return None

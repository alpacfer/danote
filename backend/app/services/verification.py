from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Literal, Protocol


class VerificationError(RuntimeError):
    """Raised when verification cannot be completed by the provider."""


@dataclass(frozen=True)
class WordVerificationMeaningSection:
    id: int
    meaning_key: str
    gloss: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    surface_forms: tuple[str, ...]


@dataclass(frozen=True)
class WordVerificationInput:
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    meaning_key: str | None
    meaning_gloss: str | None
    lexeme_source: str
    lexeme_translation: str | None
    lexeme_translation_provider: str | None
    surface_source: str | None
    lemma_pos_tag: str | None
    lemma_morphology: str | None
    surface_pos_tag: str | None
    surface_morphology: str | None
    sibling_meaning_sections: tuple[WordVerificationMeaningSection, ...] = ()


@dataclass(frozen=True)
class WordVerificationAction:
    action_type: Literal["fix_translation", "fix_gloss", "move_to_meaning_section", "move_to_lemma"]
    reason: str | None = None
    english_translation: str | None = None
    gloss: str | None = None
    target_meaning_id: int | None = None
    target_lemma: str | None = None
    target_meaning_key: str | None = None
    target_gloss: str | None = None
    target_english_translation: str | None = None
    target_pos_tag: str | None = None
    target_morphology: str | None = None


@dataclass(frozen=True)
class WordVerificationResult:
    verdict: Literal["verified", "flagged"]
    message: str
    composed_word_count: int | None = None
    problem: str | None = None
    change_to_implement: str | None = None
    suggested_actions: tuple[WordVerificationAction, ...] = ()


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
        suggested_actions = tuple(self._parse_suggested_actions(parsed.get("suggested_actions")))

        if verdict == "incorrect":
            return WordVerificationResult(
                verdict="flagged",
                message="incorrect",
                composed_word_count=word_count,
                problem=problem or "Gemini flagged lexical inconsistency in lemma, meaning, or surface-form placement.",
                change_to_implement=(
                    change_to_implement
                    or "Review the suggested action list and apply the change that makes lemma, meaning section, and forms coherent."
                ),
                suggested_actions=suggested_actions,
            )
        return WordVerificationResult(verdict="verified", message="OK", composed_word_count=word_count)

    def _verification_prompt(self, payload: WordVerificationInput) -> str:
        entry = {
            "current_entry": {
                "lemma": payload.stored_lemma,
                "surface_form": payload.stored_surface_form,
                "meaning_id": payload.meaning_id,
                "meaning_key": payload.meaning_key,
                "gloss": payload.meaning_gloss,
                "english_translation": payload.lexeme_translation,
                "lexeme_source": payload.lexeme_source,
                "translation_provider": payload.lexeme_translation_provider,
                "surface_source": payload.surface_source,
                "lemma_pos_tag": payload.lemma_pos_tag,
                "lemma_morphology": payload.lemma_morphology,
                "surface_pos_tag": payload.surface_pos_tag,
                "surface_morphology": payload.surface_morphology,
            },
            "available_meaning_sections": [
                {
                    "id": section.id,
                    "meaning_key": section.meaning_key,
                    "gloss": section.gloss,
                    "english_translation": section.english_translation,
                    "pos_tag": section.pos_tag,
                    "morphology": section.morphology,
                    "surface_forms": list(section.surface_forms),
                }
                for section in payload.sibling_meaning_sections
            ],
        }
        return (
            "You are a Professional Danish Language Expert.\n"
            "Review the current wordbank entry using the model lemma page -> meaning sections -> surface forms.\n"
            "Count if the reviewed entry is composed of multiple words.\n"
            "Return JSON only.\n"
            "{"
            '"verdict":"correct|incorrect",'
            '"word_count":0,'
            '"problem":"...",'
            '"change_to_implement":"...",'
            '"suggested_actions":['
            '{"action_type":"fix_translation","reason":"...","english_translation":"..."},'
            '{"action_type":"fix_gloss","reason":"...","gloss":"..."},'
            '{"action_type":"move_to_meaning_section","reason":"...","target_meaning_id":0},'
            '{"action_type":"move_to_lemma","reason":"...","target_lemma":"...",'
            '"target_meaning_key":"...","target_gloss":"...",'
            '"target_english_translation":"...","target_pos_tag":"...",'
            '"target_morphology":"..."}'
            "]}\n"
            "Rules:\n"
            "- Use only these four action types: fix_translation, fix_gloss, move_to_meaning_section, move_to_lemma.\n"
            "- If verdict=correct, return suggested_actions as [].\n"
            "- If action_type=move_to_meaning_section, target_meaning_id must be one of the available meaning ids.\n"
            "- If action_type=move_to_lemma, include target_lemma and target_meaning_key.\n"
            "- Discard no uncertainty into prose; use reason and structured fields instead.\n"
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
        if isinstance(parsed.get("suggested_actions"), list):
            out["suggested_actions"] = parsed["suggested_actions"]
        return out

    def _parse_suggested_actions(self, raw: object) -> list[WordVerificationAction]:
        if not isinstance(raw, list):
            return []
        actions: list[WordVerificationAction] = []
        for item in raw:
            action = self._normalize_action(item)
            if action is not None:
                actions.append(action)
        return actions

    def _normalize_action(self, raw: object) -> WordVerificationAction | None:
        if not isinstance(raw, dict):
            return None
        action_type = raw.get("action_type")
        if not isinstance(action_type, str):
            return None
        normalized_type = action_type.strip().lower()
        if normalized_type not in {
            "fix_translation",
            "fix_gloss",
            "move_to_meaning_section",
            "move_to_lemma",
        }:
            return None

        reason = _optional_clean_str(raw.get("reason"))
        if normalized_type == "fix_translation":
            english_translation = _optional_clean_str(raw.get("english_translation"))
            if not english_translation:
                return None
            return WordVerificationAction(
                action_type="fix_translation",
                reason=reason,
                english_translation=english_translation,
            )

        if normalized_type == "fix_gloss":
            gloss = _optional_clean_str(raw.get("gloss"))
            if not gloss:
                return None
            return WordVerificationAction(
                action_type="fix_gloss",
                reason=reason,
                gloss=gloss,
            )

        if normalized_type == "move_to_meaning_section":
            target_meaning_id = raw.get("target_meaning_id")
            if not isinstance(target_meaning_id, int):
                return None
            return WordVerificationAction(
                action_type="move_to_meaning_section",
                reason=reason,
                target_meaning_id=target_meaning_id,
            )

        target_lemma = _optional_clean_str(raw.get("target_lemma"))
        target_meaning_key = _optional_clean_str(raw.get("target_meaning_key"))
        if not target_lemma or not target_meaning_key:
            return None
        return WordVerificationAction(
            action_type="move_to_lemma",
            reason=reason,
            target_lemma=target_lemma,
            target_meaning_key=target_meaning_key,
            target_gloss=_optional_clean_str(raw.get("target_gloss")),
            target_english_translation=_optional_clean_str(raw.get("target_english_translation")),
            target_pos_tag=_optional_clean_str(raw.get("target_pos_tag")),
            target_morphology=_optional_clean_str(raw.get("target_morphology")),
        )

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


def _optional_clean_str(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None

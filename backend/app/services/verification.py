from __future__ import annotations

from dataclasses import dataclass, field
import json
import time
from typing import Any, Literal, Protocol

from app.services.token_classifier import normalize_token
from app.services.verification_review_policy import (
    looks_like_danish_self_translation,
    should_ignore_variation_only_review,
)


class VerificationError(RuntimeError):
    """Raised when verification cannot be completed by the provider."""


@dataclass(frozen=True)
class WordVerificationMeaningSection:
    id: int
    meaning_key: str
    gloss: str | None
    gloss_translation: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    surface_forms: tuple[str, ...]


@dataclass(frozen=True)
class WordVerificationSurfaceForm:
    form: str
    meaning_id: int | None
    meaning_key: str | None
    gloss: str | None
    gloss_translation: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    source: str | None


@dataclass(frozen=True)
class WordVerificationInput:
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    meaning_key: str | None
    meaning_gloss: str | None
    meaning_gloss_translation: str | None
    lexeme_source: str
    selected_translation: str | None
    selected_translation_scope: Literal["lemma", "meaning_section"] | None
    surface_source: str | None
    canonical_lemma: str | None
    canonical_lemma_pos_tag: str | None
    canonical_lemma_morphology: str | None
    selected_meaning_pos_tag: str | None
    selected_meaning_morphology: str | None
    selected_surface_pos_tag: str | None
    selected_surface_morphology: str | None
    current_categories: tuple[str, ...] = ()
    available_categories: tuple[str, ...] = ()
    sibling_meaning_sections: tuple[WordVerificationMeaningSection, ...] = ()
    available_surface_forms: tuple[WordVerificationSurfaceForm, ...] = ()
    review_intent: Literal["general", "complete_variations"] = "general"


@dataclass(frozen=True)
class WordVerificationAction:
    action_type: Literal["fix_translation", "fix_gloss", "fix_variations", "move_to_meaning_section", "move_to_lemma"]
    reason: str | None = None
    english_translation: str | None = None
    gloss: str | None = None
    singular_definite_form: str | None = None
    plural_indefinite_form: str | None = None
    plural_definite_form: str | None = None
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
    categories: tuple[str, ...] = ()
    suggested_actions: tuple[WordVerificationAction, ...] = ()


@dataclass(frozen=True)
class WordCategoryClassificationResult:
    categories: tuple[str, ...] = ()


class WordVerificationService(Protocol):
    provider: str
    reviewer_role: str

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult: ...
    def classify_word_categories(self, payload: WordVerificationInput) -> WordCategoryClassificationResult: ...


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
        categories = tuple(self._parse_categories(parsed, payload.available_categories))
        raw_suggested_actions = parsed.get("suggested_actions")
        suggested_actions = tuple(self._parse_suggested_actions(raw_suggested_actions, payload))

        if verdict == "incorrect":
            if should_ignore_variation_only_review(
                payload=payload,
                raw_suggested_actions=raw_suggested_actions,
                suggested_actions=suggested_actions,
            ):
                return WordVerificationResult(
                    verdict="verified",
                    message="OK",
                    composed_word_count=word_count,
                    categories=categories,
                )
            return WordVerificationResult(
                verdict="flagged",
                message="incorrect",
                composed_word_count=word_count,
                problem=problem or "Gemini flagged lexical inconsistency in lemma, meaning, or surface-form placement.",
                change_to_implement=(
                    change_to_implement
                    or "Review the suggested action list and apply the change that makes lemma, meaning section, and forms coherent."
                ),
                categories=categories,
                suggested_actions=suggested_actions,
            )
        return WordVerificationResult(
            verdict="verified",
            message="OK",
            composed_word_count=word_count,
            categories=categories,
        )

    def classify_word_categories(self, payload: WordVerificationInput) -> WordCategoryClassificationResult:
        raw = self._generate_text(self._category_prompt(payload))
        if not raw:
            return WordCategoryClassificationResult(categories=tuple())
        parsed = self._parse_response(raw)
        return WordCategoryClassificationResult(
            categories=tuple(self._parse_categories(parsed, payload.available_categories)),
        )

    def _verification_prompt(self, payload: WordVerificationInput) -> str:
        entry = self._scope_context(payload)
        completion_review = payload.review_intent == "complete_variations"
        if completion_review:
            action_examples = (
                '{"action_type":"fix_translation","reason":"...","english_translation":"..."},'
                '{"action_type":"fix_variations","reason":"...",'
                '"singular_definite_form":"...",'
                '"plural_indefinite_form":"...",'
                '"plural_definite_form":"..."},'
                '{"action_type":"move_to_meaning_section","reason":"...","target_meaning_id":0},'
                '{"action_type":"move_to_lemma","reason":"...","target_lemma":"...",'
                '"target_meaning_key":"...","target_gloss":"...",'
                '"target_english_translation":"...","target_pos_tag":"...",'
                '"target_morphology":"..."}'
            )
            fix_variations_rule = (
                "- If action_type=fix_variations, include the complete noun variation set in singular_definite_form, plural_indefinite_form, and plural_definite_form whenever those slots are known.\n"
            )
        else:
            action_examples = (
                '{"action_type":"fix_translation","reason":"...","english_translation":"..."},'
                '{"action_type":"move_to_meaning_section","reason":"...","target_meaning_id":0},'
                '{"action_type":"move_to_lemma","reason":"...","target_lemma":"...",'
                '"target_meaning_key":"...","target_gloss":"...",'
                '"target_english_translation":"...","target_pos_tag":"...",'
                '"target_morphology":"..."}'
            )
            fix_variations_rule = ""
        action_type_rule = (
            "- Use only these action types: fix_translation, move_to_meaning_section, move_to_lemma.\n"
            if not completion_review
            else "- Use only these action types: fix_translation, fix_variations, move_to_meaning_section, move_to_lemma.\n"
        )
        variation_scope_rule = (
            "- This is normal save verification. Verify only whether the saved lemma/meaning/surface placement is correct.\n"
            "- Do not require missing paradigm forms or suggest adding/correcting other variations here. Variation completeness is handled only by the Complete variations workflow.\n"
            if not completion_review
            else "- This review was triggered by Complete variations. Keep the saved lemma and meaning section fixed; verify whether the saved surface forms are valid variations for that lemma in this meaning.\n"
            "- If canonical_lemma differs from lemma during Complete variations review, treat that as a clue to re-check the completed variation set. Do not suggest move_to_lemma solely because of that mismatch.\n"
            "- When the completed variation set is wrong, describe the surface-form problem in problem/change_to_implement and use action_type=fix_variations.\n"
        )
        canonical_rule = (
            "- If canonical_lemma is present and differs from lemma, treat the saved lemma as incorrect and suggest move_to_lemma to canonical_lemma unless the entry already belongs under another provided lemma.\n"
            if not completion_review
            else ""
        )
        return (
            "You are a Professional Danish Language Expert.\n"
            "Review the current wordbank entry using the model lemma page -> meaning sections -> surface forms.\n"
            "Translations belong to the lemma or a meaning section only. Surface forms do not carry independent translations.\n"
            "Meaning glosses are immutable COR labels used only to disambiguate senses. Never suggest editing a gloss.\n"
            "Treat canonical lemma identity and metadata separately from the selected surface-form metadata.\n"
            "Use all provided context together: lemma, reviewed scope, gloss, gloss translation, translation scope, morphology, saved surface forms, and sibling meaning sections.\n"
            "Classify the reviewed word meaning into broad semantic categories.\n"
            "Count if the reviewed entry is composed of multiple words.\n"
            "Return JSON only.\n"
            "{"
            '"verdict":"correct|incorrect",'
            '"word_count":0,'
            '"problem":"...",'
            '"change_to_implement":"...",'
            '"existing_categories":["..."],'
            '"new_categories":["..."],'
            '"suggested_actions":['
            f"{action_examples}"
            "]}\n"
            "Rules:\n"
            f"{action_type_rule}"
            "- If verdict=correct, return suggested_actions as [].\n"
            "- existing_categories must be chosen from available_categories.\n"
            "- existing_categories may include multiple items, but never duplicates.\n"
            "- You may return up to 3 broad new_categories when they are genuinely useful. Otherwise return [] or omit the field.\n"
            "- New categories must be broad, reusable, and user-facing. Never return morphology, part-of-speech, or overly narrow labels.\n"
            "- If action_type=move_to_meaning_section, target_meaning_id must be one of the available meaning ids.\n"
            "- If action_type=move_to_lemma, include target_lemma and target_meaning_key.\n"
            "- Never propose gloss edits; use gloss only to identify the intended meaning section.\n"
            "- If action_type=fix_translation, english_translation must be idiomatic English. Never repeat the Danish lemma or surface form unless the translated gloss explicitly matches it.\n"
            f"{fix_variations_rule}"
            "- When meaning_gloss_translation or section gloss_translation is present, use it as the primary sense clue for homographs.\n"
            f"{variation_scope_rule}"
            f"{canonical_rule}"
            "- Discard no uncertainty into prose; use reason and structured fields instead.\n"
            f"Entry:\n{json.dumps(entry, ensure_ascii=False)}"
        )

    def _category_prompt(self, payload: WordVerificationInput) -> str:
        entry = self._scope_context(payload)
        return (
            "You are a Professional Danish Language Expert.\n"
            "Review the current wordbank scope and classify it into broad semantic categories.\n"
            "Use all provided context together: lemma, reviewed scope, gloss, gloss translation, translation scope, morphology, saved surface forms, and sibling meaning sections.\n"
            "Treat categories as reusable user-facing groups for many related words.\n"
            "Prefer matching existing categories whenever they fit.\n"
            "Return JSON only.\n"
            "{"
            '"existing_categories":["..."],'
            '"new_categories":["..."]'
            "}\n"
            "Rules:\n"
            "- existing_categories must be chosen from available_categories.\n"
            "- existing_categories may include multiple items, but never duplicates.\n"
            "- You may return up to 3 broad new_categories when they are genuinely useful.\n"
            "- New categories must be broad, reusable, and user-facing. Never return morphology, part-of-speech, or overly narrow labels.\n"
            "- If existing categories fully cover the scope, return new_categories as [] or omit it.\n"
            f"Entry:\n{json.dumps(entry, ensure_ascii=False)}"
        )

    def _scope_context(self, payload: WordVerificationInput) -> dict[str, object]:
        return {
            "current_entry": {
                "review_intent": payload.review_intent,
                "scope_type": "meaning_section" if payload.meaning_id is not None else "lemma_root",
                "lemma": payload.stored_lemma,
                "surface_form": payload.stored_surface_form,
                "meaning_id": payload.meaning_id,
                "meaning_key": payload.meaning_key,
                "gloss": payload.meaning_gloss,
                "meaning_gloss_translation": payload.meaning_gloss_translation,
                "selected_translation": payload.selected_translation,
                "selected_translation_scope": payload.selected_translation_scope,
                "lexeme_source": payload.lexeme_source,
                "surface_source": payload.surface_source,
                "canonical_lemma": payload.canonical_lemma,
                "canonical_lemma_pos_tag": payload.canonical_lemma_pos_tag,
                "canonical_lemma_morphology": payload.canonical_lemma_morphology,
                "selected_meaning_pos_tag": payload.selected_meaning_pos_tag,
                "selected_meaning_morphology": payload.selected_meaning_morphology,
                "selected_surface_pos_tag": payload.selected_surface_pos_tag,
                "selected_surface_morphology": payload.selected_surface_morphology,
                "current_categories": list(payload.current_categories),
            },
            "available_categories": list(payload.available_categories),
            "available_meaning_sections": [
                {
                    "id": section.id,
                    "meaning_key": section.meaning_key,
                    "gloss": section.gloss,
                    "gloss_translation": section.gloss_translation,
                    "english_translation": section.english_translation,
                    "pos_tag": section.pos_tag,
                    "morphology": section.morphology,
                    "surface_forms": list(section.surface_forms),
                }
                for section in payload.sibling_meaning_sections
            ],
            "available_surface_forms": [
                {
                    "form": form.form,
                    "meaning_id": form.meaning_id,
                    "meaning_key": form.meaning_key,
                    "gloss": form.gloss,
                    "gloss_translation": form.gloss_translation,
                    "english_translation": form.english_translation,
                    "pos_tag": form.pos_tag,
                    "morphology": form.morphology,
                    "source": form.source,
                }
                for form in payload.available_surface_forms
            ],
        }

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
        if isinstance(parsed.get("existing_categories"), list):
            out["existing_categories"] = parsed["existing_categories"]
        if isinstance(parsed.get("new_categories"), list):
            out["new_categories"] = parsed["new_categories"]
        if parsed.get("new_category") is None or isinstance(parsed.get("new_category"), str):
            out["new_category"] = parsed.get("new_category")
        if isinstance(parsed.get("suggested_actions"), list):
            out["suggested_actions"] = parsed["suggested_actions"]
        return out

    def _parse_categories(
        self,
        parsed: dict[str, object],
        available_categories: tuple[str, ...],
    ) -> list[str]:
        available_lookup = {
            " ".join(label.strip().split()).casefold(): label
            for label in available_categories
        }
        categories: list[str] = []
        seen: set[str] = set()
        raw_existing = parsed.get("existing_categories")
        if isinstance(raw_existing, list):
            for item in raw_existing:
                if not isinstance(item, str):
                    continue
                normalized = " ".join(item.strip().split()).casefold()
                if not normalized or normalized in seen:
                    continue
                matched = available_lookup.get(normalized)
                if matched is None:
                    continue
                seen.add(normalized)
                categories.append(matched)
        raw_new_categories = parsed.get("new_categories")
        if isinstance(raw_new_categories, list):
            for item in raw_new_categories[:3]:
                if not isinstance(item, str):
                    continue
                normalized_new = " ".join(item.strip().split())
                normalized_key = normalized_new.casefold()
                if not normalized_new or normalized_key in seen or normalized_key in available_lookup:
                    continue
                seen.add(normalized_key)
                categories.append(normalized_new)
        elif isinstance(parsed.get("new_category"), str):
            normalized_new = " ".join(str(parsed["new_category"]).strip().split())
            normalized_key = normalized_new.casefold()
            if normalized_new and normalized_key not in seen and normalized_key not in available_lookup:
                seen.add(normalized_key)
                categories.append(normalized_new)
        return categories

    def _parse_suggested_actions(
        self,
        raw: object,
        payload: WordVerificationInput,
    ) -> list[WordVerificationAction]:
        if not isinstance(raw, list):
            return []
        actions: list[WordVerificationAction] = []
        for item in raw:
            action = self._normalize_action(item, payload)
            if action is not None:
                actions.append(action)
        return actions

    def _normalize_action(
        self,
        raw: object,
        payload: WordVerificationInput,
    ) -> WordVerificationAction | None:
        if not isinstance(raw, dict):
            return None
        action_type = raw.get("action_type")
        if not isinstance(action_type, str):
            return None
        normalized_type = action_type.strip().lower()
        if normalized_type not in {
            "fix_translation",
            "fix_variations",
            "move_to_meaning_section",
            "move_to_lemma",
        }:
            return None

        reason = _optional_clean_str(raw.get("reason"))
        if normalized_type == "fix_variations":
            if payload.review_intent != "complete_variations":
                return None
            return WordVerificationAction(
                action_type="fix_variations",
                reason=reason,
                singular_definite_form=_optional_clean_str(raw.get("singular_definite_form")),
                plural_indefinite_form=_optional_clean_str(raw.get("plural_indefinite_form")),
                plural_definite_form=_optional_clean_str(raw.get("plural_definite_form")),
            )
        if normalized_type == "fix_translation":
            english_translation = _optional_clean_str(raw.get("english_translation"))
            if not english_translation:
                return None
            if looks_like_danish_self_translation(
                english_translation=english_translation,
                payload=payload,
            ):
                return None
            return WordVerificationAction(
                action_type="fix_translation",
                reason=reason,
                english_translation=english_translation,
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

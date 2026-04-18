from __future__ import annotations

from dataclasses import dataclass, field
from app.services.verification_gemini_context import category_context, verification_context
from app.services.verification_gemini_parsing import (
    parse_batch_response,
    parse_categories,
    parse_response,
    parse_suggested_actions,
)
from app.services.verification_gemini_transport import (
    ensure_client,
    generate_content,
    generate_text,
)
from app.services.verification_models import (
    VerificationError,
    WordCategoryClassificationResult,
    WordVerificationAction,
    WordVerificationInput,
    WordVerificationMeaningSection,
    WordVerificationResult,
    WordVerificationService,
    WordVerificationSurfaceForm,
)
from app.services.verification_prompt_templates import (
    build_word_category_prompt,
    build_word_verification_prompt,
)
from app.services.verification_review_policy import (
    allowed_general_action_types,
    is_surface_form_review,
    should_backfill_translation_from_gloss_hint,
    should_force_translation_fix_from_gloss_hint,
    should_ignore_gloss_hint_translation_review,
    should_ignore_morphology_supported_move_review,
    should_ignore_surface_translation_review,
    should_ignore_variation_only_review,
    should_expose_translation_hint,
)
from app.services.verification_review_text import (
    TRANSLATION_FIX_CHANGE,
    TRANSLATION_FIX_PROBLEM,
    normalize_translation_review_copy,
    should_suppress_gloss_only_feedback,
)


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
        return ensure_client(self)

    def close(self) -> None:
        self._client = None

    def verify_word_entry(self, payload: WordVerificationInput) -> WordVerificationResult:
        prompt = self._verification_prompt(payload)
        raw = self._generate_text(prompt)
        if not raw:
            return WordVerificationResult(
                verdict="flagged",
                message="Review needed",
                composed_word_count=self._infer_word_count(payload),
                problem="Could not verify the entry.",
                change_to_implement="Retry verification.",
            )
        parsed = self._parse_response(raw)
        return self._process_single_verdict(payload, parsed)

    def _process_single_verdict(
        self,
        payload: WordVerificationInput,
        parsed: dict[str, object],
    ) -> WordVerificationResult:
        """Post-process a parsed Gemini verdict dict into a WordVerificationResult."""
        fallback_word_count = self._infer_word_count(payload)

        verdict = parsed.get("verdict")
        word_count_raw = parsed.get("word_count")
        word_count = int(word_count_raw) if isinstance(word_count_raw, int) else fallback_word_count
        problem = parsed.get("problem") if isinstance(parsed.get("problem"), str) else None
        change_to_implement = (
            parsed.get("change_to_implement") if isinstance(parsed.get("change_to_implement"), str) else None
        )
        raw_suggested_actions = parsed.get("suggested_actions")
        suggested_actions = tuple(self._parse_suggested_actions(raw_suggested_actions, payload))
        if should_backfill_translation_from_gloss_hint(
            payload=payload,
            raw_suggested_actions=raw_suggested_actions,
            suggested_actions=suggested_actions,
        ):
            suggested_actions = (self._gloss_hint_translation_action(payload),)

        force_translation_fix = should_force_translation_fix_from_gloss_hint(
            payload=payload,
            suggested_actions=suggested_actions,
        )
        if force_translation_fix:
            suggested_actions = (self._gloss_hint_translation_action(payload),)
        problem, change_to_implement = normalize_translation_review_copy(
            problem=problem,
            change_to_implement=change_to_implement,
            suggested_actions=suggested_actions,
        )

        if verdict == "incorrect":
            if should_ignore_variation_only_review(
                payload=payload,
                raw_suggested_actions=raw_suggested_actions,
                suggested_actions=suggested_actions,
            ) or should_ignore_surface_translation_review(
                payload=payload,
                raw_suggested_actions=raw_suggested_actions,
                suggested_actions=suggested_actions,
                problem=problem,
                change_to_implement=change_to_implement,
            ) or should_ignore_morphology_supported_move_review(
                payload=payload,
                raw_suggested_actions=raw_suggested_actions,
                suggested_actions=suggested_actions,
            ) or should_ignore_gloss_hint_translation_review(
                payload=payload,
                raw_suggested_actions=raw_suggested_actions,
                suggested_actions=suggested_actions,
            ) or should_suppress_gloss_only_feedback(
                problem=problem,
                change_to_implement=change_to_implement,
                suggested_actions=suggested_actions,
            ):
                return WordVerificationResult(
                    verdict="verified",
                    message="OK",
                    composed_word_count=word_count,
                )
            return WordVerificationResult(
                verdict="flagged",
                message="Review needed",
                composed_word_count=word_count,
                problem=problem or "Entry placement is inconsistent.",
                change_to_implement=(
                    change_to_implement
                    or "Apply the matching structured fix."
                ),
                suggested_actions=suggested_actions,
            )
        if force_translation_fix:
            return WordVerificationResult(
                verdict="flagged",
                message="Review needed",
                composed_word_count=word_count,
                problem=problem or TRANSLATION_FIX_PROBLEM,
                change_to_implement=change_to_implement or TRANSLATION_FIX_CHANGE,
                suggested_actions=suggested_actions,
            )
        return WordVerificationResult(
            verdict="verified",
            message="OK",
            composed_word_count=word_count,
        )

    def classify_word_categories(self, payload: WordVerificationInput) -> WordCategoryClassificationResult:
        raw = self._generate_text(self._category_prompt(payload))
        if not raw:
            return WordCategoryClassificationResult(categories=tuple())
        parsed = self._parse_response(raw)
        return WordCategoryClassificationResult(
            categories=tuple(self._parse_categories(parsed, payload.available_categories)),
        )

    def verify_word_entries_batch(
        self,
        payloads: list[WordVerificationInput],
        sentence_context: str | None = None,
    ) -> list[WordVerificationResult]:
        if not payloads:
            return []
        entries = [
            {"word_id": index, **self._verification_context(payload)}
            for index, payload in enumerate(payloads)
        ]
        prompt = self._batch_verification_prompt(entries, sentence_context)
        raw = self._generate_content(prompt)
        text = getattr(raw, "text", None)
        cleaned = text.strip() if isinstance(text, str) else ""
        if not cleaned:
            return [self._batch_fallback(payload) for payload in payloads]

        parsed = self._parse_batch_response(cleaned, len(payloads))
        results: list[WordVerificationResult] = []
        for payload, word_parsed in zip(payloads, parsed, strict=False):
            if word_parsed is None:
                results.append(self._batch_fallback(payload))
            else:
                results.append(self._process_single_verdict(payload, word_parsed))
        return results

    def _batch_verification_prompt(
        self,
        entries: list[dict[str, object]],
        sentence_context: str | None = None,
    ) -> str:
        from app.services.verification_prompt_templates import build_batch_verification_prompt
        return build_batch_verification_prompt(entries=entries, sentence_context=sentence_context)

    def _parse_batch_response(
        self,
        raw: str,
        expected_count: int,
    ) -> list[dict[str, object] | None]:
        return parse_batch_response(raw, expected_count)

    def _batch_fallback(self, payload: WordVerificationInput) -> WordVerificationResult:
        return WordVerificationResult(
            verdict="flagged",
            message="Review needed",
            composed_word_count=self._infer_word_count(payload),
            problem="Batch verification failed for this entry.",
            change_to_implement="Retry verification.",
        )

    def _generate_content(self, prompt: str, *, config: object | None = None) -> object:
        return generate_content(self, prompt, config=config)

    def _verification_prompt(self, payload: WordVerificationInput) -> str:
        entry = self._verification_context(payload)
        return build_word_verification_prompt(
            entry=entry,
            completion_review=payload.review_intent == "complete_variations",
            surface_form_review=is_surface_form_review(payload),
            allowed_action_types=allowed_general_action_types(payload),
        )

    def _category_prompt(self, payload: WordVerificationInput) -> str:
        entry = self._category_context(payload)
        return build_word_category_prompt(entry=entry)

    def _verification_context(self, payload: WordVerificationInput) -> dict[str, object]:
        return verification_context(payload)

    def _category_context(self, payload: WordVerificationInput) -> dict[str, object]:
        return category_context(payload)

    def _parse_response(self, raw: str) -> dict[str, object]:
        return parse_response(raw)

    def _parse_categories(
        self,
        parsed: dict[str, object],
        available_categories: tuple[str, ...],
    ) -> list[str]:
        return parse_categories(parsed, available_categories)

    def _parse_suggested_actions(
        self,
        raw: object,
        payload: WordVerificationInput,
    ) -> list[WordVerificationAction]:
        return parse_suggested_actions(raw, payload)

    def _normalize_action(
        self,
        raw: object,
        payload: WordVerificationInput,
    ) -> WordVerificationAction | None:
        from app.services.verification_gemini_parsing import normalize_action

        return normalize_action(raw, payload)

    def _infer_word_count(self, payload: WordVerificationInput) -> int:
        source_text = payload.stored_surface_form or payload.stored_lemma
        parts = [part for part in source_text.split() if part]
        return max(1, len(parts))

    def _selected_surface_gram_raw(self, payload: WordVerificationInput) -> str | None:
        from app.services.verification_gemini_context import selected_surface_gram_raw

        return selected_surface_gram_raw(payload)

    def _gloss_hint_translation_action(self, payload: WordVerificationInput) -> WordVerificationAction:
        return WordVerificationAction(
            action_type="fix_translation",
            reason="Use the saved meaning's translated gloss.",
            english_translation=payload.meaning_gloss_translation,
        )

    def _generate_text(self, prompt: str) -> str | None:
        return generate_text(self, prompt)

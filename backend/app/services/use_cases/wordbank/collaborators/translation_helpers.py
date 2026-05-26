from __future__ import annotations

import logging

from app.services.cor_local import CORLocalEntry, CORLocalLexiconService
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.collaborators.translation_failures import (
    ProviderCallFailure,
    ProviderCallResult,
    ProviderFailureReason,
)


def provider_name(translation_service: object | None) -> str:
    provider = getattr(translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "translation"


def contextual_provider_name(gemini_word_translation_service: object | None) -> str:
    provider = getattr(gemini_word_translation_service, "provider", None)
    if isinstance(provider, str):
        cleaned = provider.strip().lower()
        if cleaned:
            return cleaned
    return "gemini_word_translation"


def normalize_comparable(value: str) -> str:
    return " ".join(value.strip().lower().split())


def is_likely_english_word(value: str) -> bool:
    normalized = value.strip().lower()
    if not normalized:
        return False
    if any(char in normalized for char in ("æ", "ø", "å")):
        return False
    parts = normalized.split()
    if not parts:
        return False
    allowed = set("abcdefghijklmnopqrstuvwxyz'-")
    for part in parts:
        if not part:
            continue
        if any(char not in allowed for char in part):
            return False
        if not any(char in "aeiouy" for char in part):
            return False
    return True


def normalize_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned.lower()


def not_configured_result(*, provider: str, operation: str) -> ProviderCallResult:
    return ProviderCallResult(
        value=None,
        failure=ProviderCallFailure(
            provider=provider,
            operation=operation,
            reason=ProviderFailureReason.NOT_CONFIGURED,
            exception_class=None,
            retryable=False,
        ),
    )


def provider_failure_result(
    *,
    logger: logging.Logger,
    provider: str,
    operation: str,
    reason: ProviderFailureReason,
    retryable: bool,
    exc: Exception,
) -> ProviderCallResult:
    failure = ProviderCallFailure(
        provider=provider,
        operation=operation,
        reason=reason,
        exception_class=exc.__class__.__name__,
        retryable=retryable,
    )
    log_provider_failure(
        logger=logger,
        provider=failure.provider,
        operation=failure.operation,
        reason=failure.reason,
        retryable=failure.retryable,
        exc=exc,
    )
    return ProviderCallResult(value=None, failure=failure)


def log_provider_failure(
    *,
    logger: logging.Logger,
    provider: str,
    operation: str,
    reason: ProviderFailureReason,
    retryable: bool,
    exc: Exception,
) -> None:
    logger.warning(
        "wordbank_translation_provider_fallback",
        extra={
            "provider": provider,
            "operation": operation,
            "failure_class": exc.__class__.__name__,
            "failure_reason": reason.value,
            "retryable": retryable,
        },
        exc_info=exc,
    )


def best_cor_local_entry_with_gloss(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    form: str,
    lemma: str,
    preferred_pos_tag: str | None,
) -> CORLocalEntry | None:
    if cor_local_lexicon_service is None:
        return None
    try:
        entries = cor_local_lexicon_service.lookup_form(form, limit=200)
    except FileNotFoundError:
        return None
    matching = [
        entry
        for entry in entries
        if normalize_token(entry.lemma) == lemma and normalize_token(entry.gloss or "")
    ]
    if not matching:
        return None
    if preferred_pos_tag:
        preferred = [entry for entry in matching if entry.pos_tag == preferred_pos_tag]
        if preferred:
            matching = preferred
    matching.sort(
        key=lambda entry: (
            0 if normalize_token(entry.form) == form else 1,
            0 if entry.norm == "N" else 1,
            entry.lemma_idx,
            entry.variation,
        )
    )
    return matching[0]


def best_cor_local_entry(
    cor_local_lexicon_service: CORLocalLexiconService | None,
    *,
    form: str,
    lemma: str,
    preferred_pos_tag: str | None,
) -> CORLocalEntry | None:
    if cor_local_lexicon_service is None:
        return None
    try:
        entries = cor_local_lexicon_service.lookup_form(form, limit=200)
    except FileNotFoundError:
        return None
    matching = [
        entry
        for entry in entries
        if normalize_token(entry.lemma) == lemma
    ]
    if not matching:
        return None
    if preferred_pos_tag:
        preferred = [entry for entry in matching if entry.pos_tag == preferred_pos_tag]
        if preferred:
            matching = preferred
    matching.sort(
        key=lambda entry: (
            0 if normalize_token(entry.form) == form else 1,
            0 if entry.norm == "N" else 1,
            entry.lemma_idx,
            entry.variation,
        )
    )
    return matching[0]

from __future__ import annotations

from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def queue_related_words_resolution(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
) -> bool:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        return False
    return runtime.related_words.queue_resolution_request(stored_lemma=normalized_lemma)

from __future__ import annotations

from collections.abc import Iterable

from app.db.repositories import WordbankBackgroundJobRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


def queue_pronunciation_generation(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    requested_forms: Iterable[str | None],
    force: bool = False,
) -> list[str]:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        return []

    pronunciation = runtime.pronunciation.queued_pronunciation_result(
        normalized_lemma,
        normalized_lemma,
    )
    if pronunciation.status != "queued":
        return []

    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        return []

    candidate_forms = _normalized_forms((normalized_lemma, *requested_forms))
    if not candidate_forms:
        return []

    if force:
        forms_to_generate = candidate_forms
    else:
        forms_to_generate = [
            form for form in candidate_forms if not _form_has_pronunciation(runtime, lexeme.id, form)
        ]

    if not forms_to_generate:
        return []

    WordbankBackgroundJobRepository(
        runtime.db_path,
        owner_user_id=runtime.owner_user_id,
    ).enqueue_pronunciation_job(
        stored_lemma=normalized_lemma,
        requested_forms=forms_to_generate,
        force=force,
    )
    return forms_to_generate


def _form_has_pronunciation(runtime: WordbankRuntime, lexeme_id: int, form: str) -> bool:
    rows = runtime.repository.find_surface_forms(lexeme_id=lexeme_id, form=form)
    return bool(rows) and all(row.has_pronunciation for row in rows)


def _normalized_forms(forms: Iterable[str | None]) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in forms:
        normalized = normalize_token(value or "")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered

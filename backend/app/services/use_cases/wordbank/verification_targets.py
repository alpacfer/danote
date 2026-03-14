from __future__ import annotations

from dataclasses import dataclass

from app.api.schemas.v1.wordbank import VerificationTargetRef
from app.db.repositories import WordbankBackgroundJobRepository
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class VerificationTarget:
    meaning_id: int | None
    stored_surface_form: str | None

    def as_ref(self) -> VerificationTargetRef:
        return VerificationTargetRef(
            meaning_id=self.meaning_id,
            stored_surface_form=self.stored_surface_form,
        )


def discover_word_page_verification_targets(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
) -> tuple[VerificationTarget, ...]:
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        return ()
    lexeme = runtime.repository.get_lexeme(normalized_lemma)
    if lexeme is None:
        return ()

    meaning_rows = runtime.repository.list_lexeme_meanings(lexeme.id)
    surface_rows = runtime.repository.list_surface_forms(lexeme.id)
    targets: list[VerificationTarget] = []
    seen: set[tuple[int | None, str | None]] = set()

    def add_target(meaning_id: int | None, stored_surface_form: str | None) -> None:
        normalized_surface = normalize_token(stored_surface_form or "") or None
        key = (meaning_id, normalized_surface)
        if key in seen:
            return
        seen.add(key)
        targets.append(VerificationTarget(meaning_id=meaning_id, stored_surface_form=normalized_surface))

    if not meaning_rows:
        add_target(None, None)
        for row in surface_rows:
            if normalize_token(row.form) == normalized_lemma:
                continue
            add_target(None, row.form)
        return tuple(targets)

    for row in surface_rows:
        if row.meaning_id is not None:
            continue
        if normalize_token(row.form) == normalized_lemma:
            add_target(None, None)
            continue
        add_target(None, row.form)

    for meaning in meaning_rows:
        add_target(meaning.id, None)
        for row in surface_rows:
            if row.meaning_id != meaning.id:
                continue
            if normalize_token(row.form) == normalized_lemma:
                continue
            add_target(meaning.id, row.form)
    return tuple(targets)


def queue_verification_targets(
    runtime: WordbankRuntime,
    *,
    stored_lemma: str,
    targets: tuple[VerificationTarget, ...],
) -> list[VerificationTargetRef]:
    repository = WordbankBackgroundJobRepository(runtime.db_path)
    queued_refs: list[VerificationTargetRef] = []
    normalized_lemma = normalize_token(stored_lemma)
    if not normalized_lemma:
        return queued_refs

    for target in targets:
        verification = runtime.verification.queued_verification_result(
            stored_surface_form=target.stored_surface_form,
        )
        runtime.verification.persist_queued_verification(
            stored_lemma=normalized_lemma,
            stored_surface_form=target.stored_surface_form,
            meaning_id=target.meaning_id,
            verification=verification,
        )
        if verification.status != "queued":
            continue
        snapshot_hash = runtime.verification.build_verification_snapshot_hash(
            stored_lemma=normalized_lemma,
            stored_surface_form=target.stored_surface_form,
            meaning_id=target.meaning_id,
        )
        repository.enqueue(
            job_type="verify_word",
            dedupe_key=(
                f"verify_word::{normalized_lemma}::{target.meaning_id or 'root'}::"
                f"{target.stored_surface_form or ''}::{snapshot_hash}"
            ),
            payload={
                "stored_lemma": normalized_lemma,
                "stored_surface_form": target.stored_surface_form,
                "meaning_id": target.meaning_id,
                "snapshot_hash": snapshot_hash,
            },
        )
        queued_refs.append(target.as_ref())
    return queued_refs

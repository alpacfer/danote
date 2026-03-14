from __future__ import annotations

from app.db.repositories.wordbank import WordbankRepository
from app.services.use_cases.wordbank.categories import (
    normalize_word_category_key,
    normalize_word_category_labels,
)


def category_labels_by_scope(
    repository: WordbankRepository,
    *,
    lexeme_id: int,
) -> dict[int | None, list[str]]:
    grouped: dict[int | None, list[str]] = {}
    for assignment in repository.list_word_category_assignments(lexeme_id):
        grouped.setdefault(assignment.meaning_id, []).append(assignment.category_label)
    return {
        scope: normalize_word_category_labels(labels)
        for scope, labels in grouped.items()
    }


def persisted_category_labels_for_scope(
    repository: WordbankRepository,
    *,
    lexeme_id: int,
    meaning_id: int | None,
) -> list[str]:
    return category_labels_by_scope(repository, lexeme_id=lexeme_id).get(meaning_id, [])


def persist_category_labels_for_scope(
    repository: WordbankRepository,
    *,
    lexeme_id: int,
    meaning_id: int | None,
    labels: list[str],
) -> list[str]:
    normalized_labels = normalize_word_category_labels(labels)
    category_ids: list[int] = []
    for label in normalized_labels:
        normalized_key = normalize_word_category_key(label)
        if normalized_key is None:
            continue
        category = repository.ensure_word_category(
            label=label,
            normalized_label=normalized_key,
        )
        category_ids.append(category.id)
    assignments = repository.replace_word_category_assignments(
        lexeme_id=lexeme_id,
        meaning_id=meaning_id,
        category_ids=category_ids,
    )
    return normalize_word_category_labels(
        assignment.category_label for assignment in assignments
    )

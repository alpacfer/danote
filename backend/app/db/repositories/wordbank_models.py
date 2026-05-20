from __future__ import annotations

import json
from dataclasses import dataclass

_QUERY_COR_IDS_SEPARATOR = "\x1f"


@dataclass(frozen=True, slots=True)
class LemmaListRow:
    lemma: str
    english_translation: str | None
    pos_tag: str | None
    variation_count: int


@dataclass(frozen=True, slots=True)
class WordbankSearchRow:
    lemma: str
    meaning_id: int | None
    meaning_key: str | None
    gloss: str | None
    cor_lemma_idx: int | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    variation_count: int
    match_surface: str | None
    query_cor_ids: list[str]


@dataclass(frozen=True, slots=True)
class LexemeRecord:
    id: int
    lemma: str
    source: str
    dictionary_status: str
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class LexemeMeaningRecord:
    id: int
    meaning_key: str
    cor_lemma_idx: int | None
    dictionary_status: str
    gloss: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None
    lexeme_id: int


@dataclass(frozen=True, slots=True)
class SurfaceFormRecord:
    id: int
    lexeme_id: int
    form: str
    source: str
    pos_tag: str | None
    morphology: str | None
    cor_id: str | None
    meaning_id: int | None
    has_pronunciation: bool


@dataclass(frozen=True, slots=True)
class RelatedWordRecord:
    id: int
    owner_lexeme_id: int
    relation_type: str
    sort_order: int
    related_lemma: str
    english_translation: str | None
    pos_tag: str | None
    preferred_cor_id: str | None = None


@dataclass(frozen=True, slots=True)
class RelatedWordWriteRecord:
    relation_type: str
    sort_order: int
    related_lemma: str
    english_translation: str | None
    pos_tag: str | None
    preferred_cor_id: str | None = None


@dataclass(frozen=True, slots=True)
class AdditionalTranslationRecord:
    id: int
    lexeme_id: int
    meaning_id: int | None
    english_translation: str
    source: str


@dataclass(frozen=True, slots=True)
class SavedWordbankTargetRecord:
    lemma: str
    meaning_id: int | None


@dataclass(frozen=True, slots=True)
class SavedTranslationTargetRecord:
    lexeme_id: int
    lemma: str
    meaning_id: int | None
    english_translation: str | None



@dataclass(frozen=True, slots=True)
class VerificationRecord:
    id: int
    lexeme_id: int
    meaning_id: int | None
    stored_surface_form: str | None
    status: str
    provider: str | None
    reviewer_role: str | None
    message: str
    problem: str | None
    change_to_implement: str | None
    suggested_actions: list[dict[str, object]]
    requested_at: str
    completed_at: str | None
    review_intent: str
    latest_snapshot_hash: str | None
    request_generation: int


@dataclass(frozen=True, slots=True)
class WordCategoryRecord:
    id: int
    label: str
    normalized_label: str


@dataclass(frozen=True, slots=True)
class WordCategoryAssignmentRecord:
    lexeme_id: int
    meaning_id: int | None
    category_id: int
    category_label: str
    category_normalized_label: str


def surface_form_from_row(row) -> SurfaceFormRecord:
    return SurfaceFormRecord(
        id=int(row["id"]),
        lexeme_id=int(row["lexeme_id"]),
        form=str(row["form"]),
        source=str(row["source"]),
        pos_tag=row["pos_tag"],
        morphology=row["morphology"],
        cor_id=row["cor_id"],
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        has_pronunciation=bool(row["has_pronunciation"]),
    )


def lexeme_meaning_from_row(row) -> LexemeMeaningRecord:
    return LexemeMeaningRecord(
        id=int(row["id"]),
        meaning_key=str(row["meaning_key"]),
        cor_lemma_idx=int(row["cor_lemma_idx"]) if row["cor_lemma_idx"] is not None else None,
        dictionary_status=str(row["dictionary_status"]) if row["dictionary_status"] is not None else "unknown",
        gloss=row["gloss"],
        english_translation=row["english_translation"],
        pos_tag=row["pos_tag"],
        morphology=row["morphology"],
        lexeme_id=int(row["lexeme_id"]),
    )


def verification_record_from_row(row) -> VerificationRecord:
    raw_actions = row["suggested_actions_json"]
    parsed_actions = json.loads(str(raw_actions)) if raw_actions else []
    if not isinstance(parsed_actions, list):
        parsed_actions = []
    return VerificationRecord(
        id=int(row["id"]),
        lexeme_id=int(row["lexeme_id"]),
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        stored_surface_form=row["stored_surface_form"],
        status=str(row["status"]),
        provider=row["provider"],
        reviewer_role=row["reviewer_role"],
        message=str(row["message"]),
        problem=row["problem"],
        change_to_implement=row["change_to_implement"],
        suggested_actions=[item for item in parsed_actions if isinstance(item, dict)],
        requested_at=str(row["requested_at"]),
        completed_at=row["completed_at"],
        review_intent=str(row["review_intent"]) if row["review_intent"] is not None else "general",
        latest_snapshot_hash=str(row["latest_snapshot_hash"]) if row["latest_snapshot_hash"] is not None else None,
        request_generation=int(row["request_generation"]) if row["request_generation"] is not None else 0,
    )


def related_word_from_row(row) -> RelatedWordRecord:
    keys = row.keys() if hasattr(row, "keys") else []
    return RelatedWordRecord(
        id=int(row["id"]),
        owner_lexeme_id=int(row["owner_lexeme_id"]),
        relation_type=str(row["relation_type"]),
        sort_order=int(row["sort_order"]),
        related_lemma=str(row["related_lemma"]),
        english_translation=row["english_translation"],
        pos_tag=row["pos_tag"],
        preferred_cor_id=row["preferred_cor_id"] if "preferred_cor_id" in keys else None,
    )


def saved_wordbank_target_from_row(row) -> SavedWordbankTargetRecord:
    return SavedWordbankTargetRecord(
        lemma=str(row["lemma"]),
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
    )


def saved_translation_target_from_row(row) -> SavedTranslationTargetRecord:
    return SavedTranslationTargetRecord(
        lexeme_id=int(row["lexeme_id"]),
        lemma=str(row["lemma"]),
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        english_translation=row["english_translation"],
    )


def additional_translation_from_row(row) -> AdditionalTranslationRecord:
    return AdditionalTranslationRecord(
        id=int(row["id"]),
        lexeme_id=int(row["lexeme_id"]),
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        english_translation=str(row["english_translation"]),
        source=str(row["source"]),
    )


def word_category_from_row(row) -> WordCategoryRecord:
    return WordCategoryRecord(
        id=int(row["id"]),
        label=str(row["label"]),
        normalized_label=str(row["normalized_label"]),
    )


def word_category_assignment_from_row(row) -> WordCategoryAssignmentRecord:
    return WordCategoryAssignmentRecord(
        lexeme_id=int(row["lexeme_id"]),
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        category_id=int(row["category_id"]),
        category_label=str(row["category_label"]),
        category_normalized_label=str(row["category_normalized_label"]),
    )


@dataclass(frozen=True, slots=True)
class VerificationChangeLogRecord:
    id: int
    stored_lemma: str
    stored_surface_form: str | None
    meaning_id: int | None
    action_type: str
    before_json: str
    after_json: str
    applied_at: str
    reverted_at: str | None
    provider: str | None


def verification_change_log_from_row(row) -> VerificationChangeLogRecord:
    return VerificationChangeLogRecord(
        id=int(row["id"]),
        stored_lemma=str(row["stored_lemma"]),
        stored_surface_form=row["stored_surface_form"],
        meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
        action_type=str(row["action_type"]),
        before_json=str(row["before_json"]),
        after_json=str(row["after_json"]),
        applied_at=str(row["applied_at"]),
        reverted_at=row["reverted_at"],
        provider=row["provider"],
    )


def parse_query_cor_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split(_QUERY_COR_IDS_SEPARATOR) if item]


__all__ = [
    "AdditionalTranslationRecord",
    "additional_translation_from_row",
    "LemmaListRow",
    "LexemeMeaningRecord",
    "lexeme_meaning_from_row",
    "LexemeRecord",
    "RelatedWordRecord",
    "related_word_from_row",
    "RelatedWordWriteRecord",
    "SavedTranslationTargetRecord",
    "saved_translation_target_from_row",
    "SavedWordbankTargetRecord",
    "saved_wordbank_target_from_row",
    "SurfaceFormRecord",
    "surface_form_from_row",
    "VerificationChangeLogRecord",
    "verification_change_log_from_row",
    "VerificationRecord",
    "verification_record_from_row",
    "WordCategoryAssignmentRecord",
    "word_category_assignment_from_row",
    "WordCategoryRecord",
    "word_category_from_row",
    "WordbankSearchRow",
]

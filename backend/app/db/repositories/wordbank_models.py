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
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class LexemeMeaningRecord:
    id: int
    meaning_key: str
    cor_lemma_idx: int | None
    gloss: str | None
    english_translation: str | None
    pos_tag: str | None
    morphology: str | None


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
        gloss=row["gloss"],
        english_translation=row["english_translation"],
        pos_tag=row["pos_tag"],
        morphology=row["morphology"],
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
    )


def parse_query_cor_ids(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [item for item in raw.split(_QUERY_COR_IDS_SEPARATOR) if item]

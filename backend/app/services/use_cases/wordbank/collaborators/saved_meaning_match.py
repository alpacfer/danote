from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.migrations import get_connection
from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class SavedMeaningMatch:
    meaning_id: int
    meaning_key: str | None
    pos_tag: str | None
    cor_lemma_idx: int | None
    gloss: str | None = None
    english_translation: str | None = None
    english_gloss: str | None = None


def load_saved_meanings_for_lemmas(
    db_path: Path,
    lemmas: list[str],
    *,
    owner_user_id: int = 1,
) -> dict[str, dict[str, list[SavedMeaningMatch]]]:
    normalized: list[str] = []
    seen: set[str] = set()
    for lemma in lemmas:
        cleaned = normalize_token(lemma or "")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        normalized.append(cleaned)
    if not normalized:
        return {}
    placeholders = ", ".join("?" for _ in normalized)
    with get_connection(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT
                l.lemma AS lemma,
                lm.id AS meaning_id,
                lm.meaning_key AS meaning_key,
                lm.pos_tag AS pos_tag,
                lm.cor_lemma_idx AS cor_lemma_idx,
                lm.gloss AS gloss,
                lm.english_translation AS english_translation,
                lm.english_gloss AS english_gloss
            FROM lexeme_meanings lm
            JOIN lexemes l ON l.id = lm.lexeme_id
            WHERE l.owner_user_id = ? AND l.lemma IN ({placeholders})
            """,
            (owner_user_id, *normalized),
        ).fetchall()
    saved: dict[str, dict[str, list[SavedMeaningMatch]]] = {}
    for row in rows:
        saved.setdefault(row["lemma"], {}).setdefault(row["meaning_key"], []).append(
            SavedMeaningMatch(
                meaning_id=int(row["meaning_id"]),
                meaning_key=row["meaning_key"],
                pos_tag=(row["pos_tag"] or "").strip().upper() or None,
                cor_lemma_idx=int(row["cor_lemma_idx"]) if row["cor_lemma_idx"] is not None else None,
                gloss=row["gloss"],
                english_translation=row["english_translation"],
                english_gloss=row["english_gloss"],
            )
        )
    return saved


def matching_saved_meaning_id(
    candidates: list[SavedMeaningMatch],
    *,
    pos_tag: str | None,
    cor_lemma_idx: int | None,
) -> int | None:
    normalized_pos = (pos_tag or "").strip().upper() or None
    for candidate in candidates:
        if cor_lemma_idx is not None and candidate.cor_lemma_idx is not None:
            if candidate.cor_lemma_idx != cor_lemma_idx:
                continue
        elif normalized_pos is not None and candidate.pos_tag is not None:
            if candidate.pos_tag != normalized_pos:
                continue
        return candidate.meaning_id
    return None


def semantic_matching_saved_meaning_id(
    candidates: list[SavedMeaningMatch],
    *,
    pos_tag: str | None,
    cor_lemma_idx: int | None,
    meaning_key: str | None,
    gloss: str | None,
    english_translation: str | None,
) -> int | None:
    requested_keys = _normalized_value_set(meaning_key, gloss, english_translation)
    if not requested_keys:
        return None
    normalized_pos = (pos_tag or "").strip().upper() or None
    for candidate in candidates:
        if cor_lemma_idx is not None and candidate.cor_lemma_idx is not None:
            if candidate.cor_lemma_idx != cor_lemma_idx:
                continue
        if normalized_pos is not None and candidate.pos_tag is not None:
            if candidate.pos_tag != normalized_pos:
                continue
        candidate_keys = _normalized_value_set(
            candidate.meaning_key,
            candidate.gloss,
            candidate.english_translation,
            candidate.english_gloss,
        )
        if requested_keys & candidate_keys:
            return candidate.meaning_id
    return None


def _normalized_value_set(*values: str | None) -> set[str]:
    return {
        normalized
        for value in values
        if (normalized := normalize_token(value or ""))
    }

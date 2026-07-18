from __future__ import annotations

from pathlib import Path

from app.db.repositories.wordbank_models import LemmaListRow, LemmaTranslationGroupRow
from app.db.sqlite import get_connection, timed_db_operation


class WordbankLemmaListReadRepository:
    _db_path: Path
    _owner_user_id: int

    def list_lemmas(self) -> list[LemmaListRow]:
        with timed_db_operation("wordbank.list_lemmas"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                WITH meaning_counts AS (
                    SELECT lexeme_id, COUNT(*) AS meaning_count
                    FROM lexeme_meanings
                    GROUP BY lexeme_id
                ),
                single_meanings AS (
                    SELECT
                        lm.lexeme_id,
                        lm.english_translation,
                        lm.pos_tag
                    FROM lexeme_meanings lm
                    JOIN meaning_counts mc
                      ON mc.lexeme_id = lm.lexeme_id
                     AND mc.meaning_count = 1
                ),
                surface_counts AS (
                    SELECT
                        sf.lexeme_id,
                        COUNT(DISTINCT CASE WHEN sf.form <> l.lemma THEN sf.form END) AS variation_count
                    FROM surface_forms sf
                    JOIN lexemes l ON l.id = sf.lexeme_id
                    GROUP BY sf.lexeme_id
                ),
                pos_tag_values AS (
                    SELECT id AS lexeme_id, UPPER(TRIM(pos_tag)) AS pos_tag
                    FROM lexemes
                    WHERE pos_tag IS NOT NULL AND TRIM(pos_tag) <> ''
                    UNION
                    SELECT lexeme_id, UPPER(TRIM(pos_tag)) AS pos_tag
                    FROM lexeme_meanings
                    WHERE pos_tag IS NOT NULL AND TRIM(pos_tag) <> ''
                    UNION
                    SELECT lexeme_id, UPPER(TRIM(pos_tag)) AS pos_tag
                    FROM surface_forms
                    WHERE pos_tag IS NOT NULL AND TRIM(pos_tag) <> ''
                ),
                pos_tag_rollups AS (
                    SELECT lexeme_id, GROUP_CONCAT(pos_tag) AS pos_tags
                    FROM (
                        SELECT DISTINCT lexeme_id, pos_tag
                        FROM pos_tag_values
                        ORDER BY pos_tag COLLATE NOCASE
                    )
                    GROUP BY lexeme_id
                ),
                category_rollups AS (
                    SELECT lexeme_id, GROUP_CONCAT(label, CHAR(31)) AS categories
                    FROM (
                        SELECT DISTINCT
                            wca.lexeme_id,
                            wc.label,
                            wc.normalized_label
                        FROM wordbank_category_assignments wca
                        JOIN wordbank_categories wc ON wc.id = wca.category_id
                        ORDER BY wc.normalized_label COLLATE NOCASE
                    )
                    GROUP BY lexeme_id
                ),
                meaning_activity AS (
                    SELECT lexeme_id, MAX(updated_at) AS latest_at
                    FROM lexeme_meanings
                    GROUP BY lexeme_id
                ),
                surface_activity AS (
                    SELECT lexeme_id, MAX(created_at) AS latest_at
                    FROM surface_forms
                    GROUP BY lexeme_id
                ),
                category_activity AS (
                    SELECT lexeme_id, MAX(updated_at) AS latest_at
                    FROM wordbank_category_assignments
                    GROUP BY lexeme_id
                )
                SELECT
                    l.id AS lexeme_id,
                    l.lemma,
                    l.created_at,
                    MAX(
                        l.updated_at,
                        COALESCE(ma.latest_at, l.created_at),
                        COALESCE(sa.latest_at, l.created_at),
                        COALESCE(ca.latest_at, l.created_at)
                    ) AS last_enriched_at,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) = 0 THEN l.english_translation
                        WHEN mc.meaning_count = 1 THEN COALESCE(sm.english_translation, l.english_translation)
                        ELSE NULL
                    END AS english_translation,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) = 0 THEN l.pos_tag
                        WHEN mc.meaning_count = 1 THEN COALESCE(sm.pos_tag, l.pos_tag)
                        ELSE NULL
                    END AS pos_tag,
                    COALESCE(ptr.pos_tags, '') AS pos_tags,
                    COALESCE(cr.categories, '') AS categories,
                    COALESCE(sc.variation_count, 0) AS variation_count
                FROM lexemes l
                LEFT JOIN meaning_counts mc ON mc.lexeme_id = l.id
                LEFT JOIN single_meanings sm ON sm.lexeme_id = l.id
                LEFT JOIN surface_counts sc ON sc.lexeme_id = l.id
                LEFT JOIN pos_tag_rollups ptr ON ptr.lexeme_id = l.id
                LEFT JOIN category_rollups cr ON cr.lexeme_id = l.id
                LEFT JOIN meaning_activity ma ON ma.lexeme_id = l.id
                LEFT JOIN surface_activity sa ON sa.lexeme_id = l.id
                LEFT JOIN category_activity ca ON ca.lexeme_id = l.id
                WHERE l.owner_user_id = ?
                ORDER BY l.lemma COLLATE NOCASE
                """,
                (self._owner_user_id,),
            ).fetchall()
            translation_rows = conn.execute(
                """
                WITH meaning_counts AS (
                    SELECT lexeme_id, COUNT(*) AS meaning_count
                    FROM lexeme_meanings
                    GROUP BY lexeme_id
                )
                SELECT
                    l.id AS lexeme_id,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) > 0 THEN lm.id
                        ELSE NULL
                    END AS meaning_id,
                    CASE
                        WHEN COALESCE(mc.meaning_count, 0) > 0 THEN lm.english_translation
                        ELSE l.english_translation
                    END AS english_translation,
                    wat.english_translation AS additional_translation
                FROM lexemes l
                LEFT JOIN meaning_counts mc ON mc.lexeme_id = l.id
                LEFT JOIN lexeme_meanings lm
                  ON lm.lexeme_id = l.id
                 AND COALESCE(mc.meaning_count, 0) > 0
                LEFT JOIN wordbank_additional_translations wat
                  ON wat.lexeme_id = l.id
                 AND (
                    (COALESCE(mc.meaning_count, 0) > 0 AND wat.meaning_id = lm.id)
                    OR
                    (COALESCE(mc.meaning_count, 0) = 0 AND wat.meaning_id IS NULL)
                 )
                WHERE l.owner_user_id = ?
                ORDER BY l.id ASC, lm.id ASC, wat.id ASC
                """,
                (self._owner_user_id,),
            ).fetchall()

        translation_groups_by_lexeme = _translation_groups_by_lexeme(translation_rows)
        return [
            LemmaListRow(
                lemma=str(row["lemma"]),
                created_at=str(row["created_at"]),
                last_enriched_at=str(row["last_enriched_at"]),
                english_translation=row["english_translation"],
                pos_tag=row["pos_tag"],
                pos_tags=tuple(_split_list_field(row["pos_tags"], ",")),
                categories=tuple(_split_list_field(row["categories"], "\x1f")),
                variation_count=int(row["variation_count"]),
                translation_groups=translation_groups_by_lexeme.get(int(row["lexeme_id"]), ()),
            )
            for row in rows
        ]


def _translation_groups_by_lexeme(rows) -> dict[int, tuple[LemmaTranslationGroupRow, ...]]:
    grouped: dict[int, dict[int | None, tuple[str | None, list[str]]]] = {}
    for row in rows:
        lexeme_id = int(row["lexeme_id"])
        meaning_id = int(row["meaning_id"]) if row["meaning_id"] is not None else None
        lexeme_groups = grouped.setdefault(lexeme_id, {})
        primary = _clean_translation(row["english_translation"])
        if meaning_id not in lexeme_groups:
            lexeme_groups[meaning_id] = (primary, [])
        additional = _clean_translation(row["additional_translation"])
        if additional is not None:
            lexeme_groups[meaning_id][1].append(additional)

    return {
        lexeme_id: tuple(_translation_groups(lexeme_groups))
        for lexeme_id, lexeme_groups in grouped.items()
    }


def _translation_groups(
    grouped_values: dict[int | None, tuple[str | None, list[str]]],
):
    for primary, additional_values in grouped_values.values():
        seen = {primary.casefold()} if primary is not None else set()
        additional_translations: list[str] = []
        for value in additional_values:
            normalized = value.casefold()
            if normalized in seen:
                continue
            seen.add(normalized)
            additional_translations.append(value)
        if primary is not None or additional_translations:
            yield LemmaTranslationGroupRow(
                english_translation=primary,
                additional_translations=tuple(additional_translations),
            )


def _clean_translation(value: object) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def _split_list_field(value: str | None, separator: str) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in str(value).split(separator) if part.strip()]

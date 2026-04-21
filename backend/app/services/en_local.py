from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path


def _normalize_space(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


@dataclass(frozen=True)
class ENLocalEntry:
    en_id: str
    lemma: str
    pos_raw: str
    pos_ud: str
    sense_idx: int
    gloss: str
    examples: list[str]
    ipa: str | None


@dataclass(frozen=True)
class ENLocalFormMatch:
    form: str
    lemma: str
    pos_ud: str
    tags: list[str]


@dataclass
class ENLocalLexiconService:
    db_path: Path
    provider: str = "en_local"

    def has_form(self, value: str) -> bool:
        normalized = _normalize_space(value).lower()
        if not normalized:
            return False
        rows = self._query_rows(
            "SELECT 1 FROM en_forms WHERE form_lower = ? LIMIT 1",
            (normalized,),
        )
        return bool(rows)

    def lookup_form(self, value: str) -> list[ENLocalFormMatch]:
        normalized = _normalize_space(value).lower()
        if not normalized:
            return []
        rows = self._query_rows(
            """
            SELECT f.form, f.lemma, f.pos_ud, f.tags_json,
                   (SELECT COUNT(*) FROM en_entries e
                     WHERE e.lemma_lower = lower(f.lemma) AND e.pos_ud = f.pos_ud) AS sense_count
              FROM en_forms f
             WHERE f.form_lower = ?
             ORDER BY
                sense_count DESC,
                CASE WHEN f.tags_json != '[]' AND lower(f.lemma) != ? THEN 0 ELSE 1 END,
                CASE WHEN lower(f.lemma) = ? THEN 0 ELSE 1 END,
                f.lemma
            """,
            (normalized, normalized, normalized),
        )
        best_by_pos: dict[str, ENLocalFormMatch] = {}
        for row in rows:
            lemma = str(row["lemma"])
            pos_ud = str(row["pos_ud"])
            sense_count = int(row["sense_count"] or 0)
            if sense_count < 1:
                continue
            if pos_ud in best_by_pos:
                continue
            try:
                tags = json.loads(row["tags_json"]) if row["tags_json"] else []
            except (TypeError, ValueError):
                tags = []
            if not isinstance(tags, list):
                tags = []
            best_by_pos[pos_ud] = ENLocalFormMatch(
                form=str(row["form"]),
                lemma=lemma,
                pos_ud=pos_ud,
                tags=[str(t) for t in tags],
            )
        return list(best_by_pos.values())

    def lookup_lemma_senses(self, lemma: str, pos_ud: str | None = None) -> list[ENLocalEntry]:
        normalized = _normalize_space(lemma).lower()
        if not normalized:
            return []
        if pos_ud:
            rows = self._query_rows(
                """
                SELECT en_id, lemma, pos_raw, pos_ud, sense_idx, gloss, examples_json, ipa
                  FROM en_entries
                 WHERE lemma_lower = ? AND pos_ud = ?
                 ORDER BY sense_idx
                """,
                (normalized, pos_ud),
            )
        else:
            rows = self._query_rows(
                """
                SELECT en_id, lemma, pos_raw, pos_ud, sense_idx, gloss, examples_json, ipa
                  FROM en_entries
                 WHERE lemma_lower = ?
                 ORDER BY pos_ud, sense_idx
                """,
                (normalized,),
            )
        return [self._row_to_entry(row) for row in rows]

    def _row_to_entry(self, row: sqlite3.Row) -> ENLocalEntry:
        try:
            examples = json.loads(row["examples_json"]) if row["examples_json"] else []
        except (TypeError, ValueError):
            examples = []
        if not isinstance(examples, list):
            examples = []
        return ENLocalEntry(
            en_id=str(row["en_id"]),
            lemma=str(row["lemma"]),
            pos_raw=str(row["pos_raw"]),
            pos_ud=str(row["pos_ud"]),
            sense_idx=int(row["sense_idx"]),
            gloss=str(row["gloss"]),
            examples=[str(e) for e in examples],
            ipa=row["ipa"] if row["ipa"] else None,
        )

    def _query_rows(self, sql: str, params: tuple[object, ...]) -> list[sqlite3.Row]:
        if not self.db_path.exists():
            return []
        with self._connect_read_only() as conn:
            return conn.execute(sql, params).fetchall()

    def _connect_read_only(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

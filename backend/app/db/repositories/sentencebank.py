from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection, timed_db_operation


@dataclass(frozen=True, slots=True)
class SentenceRecord:
    id: int
    source_text: str
    english_translation: str | None
    created_at: str


class SentencebankRepository:
    def __init__(self, db_path: Path):
        self._db_path = db_path

    def find_by_normalized_sentence(self, normalized_sentence: str) -> SentenceRecord | None:
        with timed_db_operation("sentencebank.find_by_normalized_sentence"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT id, source_sentence, english_translation, created_at
                FROM sentence_bank
                WHERE normalized_sentence = ?
                LIMIT 1
                """,
                (normalized_sentence,),
            ).fetchone()
        if row is None:
            return None
        return SentenceRecord(
            id=int(row["id"]),
            source_text=str(row["source_sentence"]),
            english_translation=row["english_translation"],
            created_at=str(row["created_at"]),
        )

    def insert_sentence(
        self,
        *,
        source_text: str,
        normalized_sentence: str,
        english_translation: str | None,
        translation_provider: str | None,
    ) -> None:
        with timed_db_operation("sentencebank.insert_sentence"), get_connection(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO sentence_bank (
                    source_sentence,
                    normalized_sentence,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    source_text,
                    normalized_sentence,
                    english_translation,
                    translation_provider,
                ),
            )

    def list_sentences(self) -> list[SentenceRecord]:
        with timed_db_operation("sentencebank.list_sentences"), get_connection(self._db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT id, source_sentence, english_translation, created_at
                FROM sentence_bank
                ORDER BY datetime(created_at) DESC, id DESC
                """
            ).fetchall()
        return [
            SentenceRecord(
                id=int(row["id"]),
                source_text=str(row["source_sentence"]),
                english_translation=row["english_translation"],
                created_at=str(row["created_at"]),
            )
            for row in rows
        ]

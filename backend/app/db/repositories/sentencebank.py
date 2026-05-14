from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.sqlite import get_connection, timed_db_operation


@dataclass(frozen=True, slots=True)
class SentenceTokenRecord:
    token_index: int
    surface_form: str
    normalized_surface: str
    lemma_candidate: str | None
    stored_lemma: str | None
    lexeme_id: int | None
    meaning_id: int | None
    cor_id: str | None
    pos_tag: str | None
    morphology: str | None
    gloss: str | None
    english_translation: str | None
    gloss_translation: str | None
    save_status: str = "saved"


@dataclass(frozen=True, slots=True)
class SentenceTokenWriteRecord:
    token_index: int
    surface_form: str
    normalized_surface: str
    lemma_candidate: str | None
    stored_lemma: str | None
    lexeme_id: int | None
    meaning_id: int | None
    cor_id: str | None
    pos_tag: str | None
    morphology: str | None
    gloss: str | None
    english_translation: str | None
    gloss_translation: str | None
    save_status: str = "saved"


@dataclass(frozen=True, slots=True)
class SentenceRecord:
    id: int
    source_text: str
    english_translation: str | None
    created_at: str
    has_pronunciation: bool = False
    tokens: tuple[SentenceTokenRecord, ...] = ()
    matched_token_indexes: tuple[int, ...] = ()


class SentencebankRepository:
    def __init__(self, db_path: Path, *, owner_user_id: int = 1):
        self._db_path = db_path
        self._owner_user_id = owner_user_id

    def find_by_normalized_sentence(self, normalized_sentence: str) -> SentenceRecord | None:
        with timed_db_operation("sentencebank.find_by_normalized_sentence"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    source_sentence,
                    english_translation,
                    created_at,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM sentence_bank
                WHERE owner_user_id = ? AND normalized_sentence = ?
                LIMIT 1
                """,
                (self._owner_user_id, normalized_sentence),
            ).fetchone()
            if row is None:
                return None
            sentence_ids = [int(row["id"])]
            tokens_by_sentence = self._fetch_tokens_by_sentence(conn, sentence_ids)
        return self._sentence_record_from_row(row, tokens_by_sentence=tokens_by_sentence)

    def get_sentence(self, sentence_id: int) -> SentenceRecord | None:
        with timed_db_operation("sentencebank.get_sentence"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            row = conn.execute(
                """
                SELECT
                    id,
                    source_sentence,
                    english_translation,
                    created_at,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM sentence_bank
                WHERE id = ? AND owner_user_id = ?
                LIMIT 1
                """,
                (sentence_id, self._owner_user_id),
            ).fetchone()
            if row is None:
                return None
            sentence_ids = [int(row["id"])]
            tokens_by_sentence = self._fetch_tokens_by_sentence(conn, sentence_ids)
        return self._sentence_record_from_row(row, tokens_by_sentence=tokens_by_sentence)

    def insert_sentence(
        self,
        *,
        source_text: str,
        normalized_sentence: str,
        english_translation: str | None,
        translation_provider: str | None,
    ) -> int:
        with timed_db_operation("sentencebank.insert_sentence"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sentence_bank (
                    owner_user_id,
                    source_sentence,
                    normalized_sentence,
                    english_translation,
                    translation_provider
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    self._owner_user_id,
                    source_text,
                    normalized_sentence,
                    english_translation,
                    translation_provider,
                ),
            )
        assert cursor.lastrowid is not None
        return int(cursor.lastrowid)

    def replace_sentence_tokens(
        self,
        *,
        sentence_id: int,
        tokens: list[SentenceTokenWriteRecord],
    ) -> None:
        with timed_db_operation("sentencebank.replace_sentence_tokens"), get_connection(self._db_path) as conn:
            if not self._sentence_belongs_to_owner(conn, sentence_id):
                raise LookupError("sentence was not found")
            conn.execute(
                """
                DELETE FROM sentence_bank_tokens
                WHERE sentence_id = ?
                  AND EXISTS (
                    SELECT 1 FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (sentence_id, self._owner_user_id),
            )
            if not tokens:
                return
            conn.executemany(
                """
                INSERT INTO sentence_bank_tokens (
                    sentence_id,
                    token_index,
                    surface_form,
                    normalized_surface,
                    lemma_candidate,
                    stored_lemma,
                    lexeme_id,
                    meaning_id,
                    cor_id,
                    pos_tag,
                    morphology,
                    gloss,
                    english_translation,
                    gloss_translation,
                    save_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        sentence_id,
                        token.token_index,
                        token.surface_form,
                        token.normalized_surface,
                        token.lemma_candidate,
                        token.stored_lemma,
                        token.lexeme_id,
                        token.meaning_id,
                        token.cor_id,
                        token.pos_tag,
                        token.morphology,
                        token.gloss,
                        token.english_translation,
                        token.gloss_translation,
                        token.save_status,
                    )
                    for token in tokens
                ],
            )

    def replace_sentence_token(
        self,
        *,
        sentence_id: int,
        token: SentenceTokenWriteRecord,
    ) -> None:
        with timed_db_operation("sentencebank.replace_sentence_token"), get_connection(self._db_path) as conn:
            if not self._sentence_belongs_to_owner(conn, sentence_id):
                raise LookupError("sentence was not found")
            conn.execute(
                """
                DELETE FROM sentence_bank_tokens
                WHERE sentence_id = ?
                  AND token_index = ?
                  AND EXISTS (
                    SELECT 1 FROM sentence_bank sb
                    WHERE sb.id = sentence_bank_tokens.sentence_id
                      AND sb.owner_user_id = ?
                  )
                """,
                (sentence_id, token.token_index, self._owner_user_id),
            )
            conn.execute(
                """
                INSERT INTO sentence_bank_tokens (
                    sentence_id,
                    token_index,
                    surface_form,
                    normalized_surface,
                    lemma_candidate,
                    stored_lemma,
                    lexeme_id,
                    meaning_id,
                    cor_id,
                    pos_tag,
                    morphology,
                    gloss,
                    english_translation,
                    gloss_translation,
                    save_status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sentence_id,
                    token.token_index,
                    token.surface_form,
                    token.normalized_surface,
                    token.lemma_candidate,
                    token.stored_lemma,
                    token.lexeme_id,
                    token.meaning_id,
                    token.cor_id,
                    token.pos_tag,
                    token.morphology,
                    token.gloss,
                    token.english_translation,
                    token.gloss_translation,
                    token.save_status,
                ),
            )

    def list_sentences(self) -> list[SentenceRecord]:
        with timed_db_operation("sentencebank.list_sentences"), get_connection(self._db_path, read_only=True) as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    source_sentence,
                    english_translation,
                    created_at,
                    CASE WHEN pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM sentence_bank
                WHERE owner_user_id = ?
                ORDER BY datetime(created_at) DESC, id DESC
                """,
                (self._owner_user_id,),
            ).fetchall()
            sentence_ids = [int(row["id"]) for row in rows]
            tokens_by_sentence = self._fetch_tokens_by_sentence(conn, sentence_ids)
        return [self._sentence_record_from_row(row, tokens_by_sentence=tokens_by_sentence) for row in rows]

    def list_linked_sentences_for_lemma(self, stored_lemma: str) -> list[SentenceRecord]:
        with timed_db_operation("sentencebank.list_linked_sentences_for_lemma"), get_connection(
            self._db_path, read_only=True
        ) as conn:
            rows = conn.execute(
                """
                SELECT
                    sb.id,
                    sb.source_sentence,
                    sb.english_translation,
                    sb.created_at,
                    CASE WHEN sb.pronunciation_audio IS NOT NULL THEN 1 ELSE 0 END AS has_pronunciation
                FROM sentence_bank sb
                WHERE sb.owner_user_id = ?
                  AND EXISTS (
                    SELECT 1
                    FROM sentence_bank_tokens sbt
                    WHERE sbt.sentence_id = sb.id
                      AND sbt.stored_lemma = ?
                )
                ORDER BY datetime(sb.created_at) DESC, sb.id DESC
                """,
                (self._owner_user_id, stored_lemma),
            ).fetchall()
            sentence_ids = [int(row["id"]) for row in rows]
            tokens_by_sentence = self._fetch_tokens_by_sentence(conn, sentence_ids)
            matched_indexes_by_sentence = self._fetch_matched_token_indexes(
                conn,
                sentence_ids=sentence_ids,
                stored_lemma=stored_lemma,
            )
        return [
            SentenceRecord(
                id=int(row["id"]),
                source_text=str(row["source_sentence"]),
                english_translation=row["english_translation"],
                created_at=str(row["created_at"]),
                has_pronunciation=bool(row["has_pronunciation"]),
                tokens=tuple(tokens_by_sentence.get(int(row["id"]), ())),
                matched_token_indexes=tuple(matched_indexes_by_sentence.get(int(row["id"]), ())),
            )
            for row in rows
        ]

    def update_pronunciation(
        self,
        *,
        sentence_id: int,
        audio_bytes: bytes,
        mime_type: str,
        provider: str | None,
        model: str | None,
    ) -> bool:
        with timed_db_operation("sentencebank.update_pronunciation"), get_connection(self._db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE sentence_bank
                SET pronunciation_audio = ?,
                    pronunciation_mime_type = ?,
                    pronunciation_provider = ?,
                    pronunciation_model = ?,
                    pronunciation_generated_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND owner_user_id = ?
                """,
                (audio_bytes, mime_type, provider, model, sentence_id, self._owner_user_id),
            )
        return cursor.rowcount == 1

    def _fetch_tokens_by_sentence(self, conn, sentence_ids: list[int]) -> dict[int, list[SentenceTokenRecord]]:
        if not sentence_ids:
            return {}
        placeholders = ", ".join("?" for _ in sentence_ids)
        rows = conn.execute(
            f"""
            SELECT
                sentence_id,
                token_index,
                surface_form,
                normalized_surface,
                lemma_candidate,
                stored_lemma,
                lexeme_id,
                meaning_id,
                cor_id,
                pos_tag,
                morphology,
                gloss,
                english_translation,
                gloss_translation,
                save_status
            FROM sentence_bank_tokens
            WHERE sentence_id IN ({placeholders})
            ORDER BY sentence_id ASC, token_index ASC, id ASC
            """,
            tuple(sentence_ids),
        ).fetchall()
        grouped: dict[int, list[SentenceTokenRecord]] = {}
        for row in rows:
            sentence_id = int(row["sentence_id"])
            grouped.setdefault(sentence_id, []).append(
                SentenceTokenRecord(
                    token_index=int(row["token_index"]),
                    surface_form=str(row["surface_form"]),
                    normalized_surface=str(row["normalized_surface"]),
                    lemma_candidate=str(row["lemma_candidate"]) if row["lemma_candidate"] is not None else None,
                    stored_lemma=str(row["stored_lemma"]) if row["stored_lemma"] is not None else None,
                    lexeme_id=int(row["lexeme_id"]) if row["lexeme_id"] is not None else None,
                    meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
                    cor_id=row["cor_id"],
                    pos_tag=row["pos_tag"],
                    morphology=row["morphology"],
                    gloss=row["gloss"],
                    english_translation=row["english_translation"],
                    gloss_translation=row["gloss_translation"],
                    save_status=str(row["save_status"] or "saved"),
                )
            )
        return grouped

    def _sentence_belongs_to_owner(self, conn, sentence_id: int) -> bool:
        return (
            conn.execute(
                "SELECT 1 FROM sentence_bank WHERE id = ? AND owner_user_id = ? LIMIT 1",
                (sentence_id, self._owner_user_id),
            ).fetchone()
            is not None
        )

    def _fetch_matched_token_indexes(
        self,
        conn,
        *,
        sentence_ids: list[int],
        stored_lemma: str,
    ) -> dict[int, list[int]]:
        if not sentence_ids:
            return {}
        placeholders = ", ".join("?" for _ in sentence_ids)
        rows = conn.execute(
            f"""
            SELECT sentence_id, token_index
            FROM sentence_bank_tokens
            WHERE stored_lemma = ?
              AND sentence_id IN ({placeholders})
            ORDER BY sentence_id ASC, token_index ASC
            """,
            (stored_lemma, *sentence_ids),
        ).fetchall()
        grouped: dict[int, list[int]] = {}
        for row in rows:
            grouped.setdefault(int(row["sentence_id"]), []).append(int(row["token_index"]))
        return grouped

    def _sentence_record_from_row(
        self,
        row,
        *,
        tokens_by_sentence: dict[int, list[SentenceTokenRecord]],
    ) -> SentenceRecord:
        sentence_id = int(row["id"])
        return SentenceRecord(
            id=sentence_id,
            source_text=str(row["source_sentence"]),
            english_translation=row["english_translation"],
            created_at=str(row["created_at"]),
            has_pronunciation=bool(row["has_pronunciation"]),
            tokens=tuple(tokens_by_sentence.get(sentence_id, ())),
        )

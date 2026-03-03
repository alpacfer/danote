from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3


COR_ID_PATTERN = re.compile(r"^COR\.(\d+)\.(\d{3})\.(\d{2})$")


@dataclass(frozen=True)
class CORImportStats:
    total_rows: int
    inserted_rows: int
    skipped_rows: int
    malformed_id_rows: int
    malformed_column_rows: int
    missing_required_rows: int


def parse_cor_id(cor_id: str) -> tuple[int, int, int] | None:
    match = COR_ID_PATTERN.fullmatch(cor_id.strip())
    if match is None:
        return None
    lemma_idx_str, gram_code_str, variation_str = match.groups()
    return int(lemma_idx_str), int(gram_code_str), int(variation_str)


def build_cor_sqlite(
    *,
    input_path: Path,
    output_path: Path,
    batch_size: int = 50_000,
) -> CORImportStats:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if not input_path.exists():
        raise FileNotFoundError(f"Input TSV not found at {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(output_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        _create_schema(conn)

        total_rows = 0
        inserted_rows = 0
        skipped_rows = 0
        malformed_id_rows = 0
        malformed_column_rows = 0
        missing_required_rows = 0
        batch: list[tuple[object, ...]] = []

        with input_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                total_rows += 1
                line = raw_line.rstrip("\n")
                columns = line.split("\t")
                if len(columns) != 6:
                    skipped_rows += 1
                    malformed_column_rows += 1
                    continue

                cor_id, lemma, gloss, gram, form, norm = (value.strip() for value in columns)
                if not cor_id or not lemma or not gram or not form:
                    skipped_rows += 1
                    missing_required_rows += 1
                    continue

                parsed = parse_cor_id(cor_id)
                if parsed is None:
                    skipped_rows += 1
                    malformed_id_rows += 1
                    continue
                lemma_idx, gram_code, variation = parsed

                batch.append(
                    (
                        cor_id,
                        lemma.lower(),
                        gloss,
                        gram.lower(),
                        form.lower(),
                        norm.upper(),
                        lemma_idx,
                        gram_code,
                        variation,
                    )
                )
                if len(batch) >= batch_size:
                    inserted_rows += _insert_batch(conn, batch)
                    batch.clear()

        if batch:
            inserted_rows += _insert_batch(conn, batch)
            batch.clear()

        _create_indexes(conn)
        conn.commit()
        return CORImportStats(
            total_rows=total_rows,
            inserted_rows=inserted_rows,
            skipped_rows=skipped_rows,
            malformed_id_rows=malformed_id_rows,
            malformed_column_rows=malformed_column_rows,
            missing_required_rows=missing_required_rows,
        )
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE cor_entries (
            cor_id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL,
            gloss TEXT,
            gram TEXT NOT NULL,
            form TEXT NOT NULL,
            norm TEXT NOT NULL,
            lemma_idx INTEGER NOT NULL,
            gram_code INTEGER NOT NULL,
            variation INTEGER NOT NULL
        )
        """
    )


def _insert_batch(conn: sqlite3.Connection, batch: list[tuple[object, ...]]) -> int:
    cursor = conn.executemany(
        """
        INSERT INTO cor_entries (
            cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        batch,
    )
    return cursor.rowcount if cursor.rowcount is not None and cursor.rowcount >= 0 else len(batch)


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX idx_cor_form ON cor_entries(form)")
    conn.execute("CREATE INDEX idx_cor_form_lower ON cor_entries(lower(form))")
    conn.execute("CREATE INDEX idx_cor_lemma_idx ON cor_entries(lemma_idx)")
    conn.execute("CREATE INDEX idx_cor_lemma_gram ON cor_entries(lemma, gram)")

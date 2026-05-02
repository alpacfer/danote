from __future__ import annotations

import sqlite3

from app.core.config import Settings

__test__ = False


def _create_cor_entries_table(conn: sqlite3.Connection) -> None:
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
    conn.execute("CREATE INDEX idx_cor_form ON cor_entries(form)")
    conn.execute("CREATE INDEX idx_cor_form_lower ON cor_entries(lower(form))")
    conn.execute("CREATE INDEX idx_cor_lemma_idx ON cor_entries(lemma_idx)")
    conn.execute("CREATE INDEX idx_cor_lemma_gram ON cor_entries(lemma, gram)")


def _insert_cor_entries(conn: sqlite3.Connection, rows: tuple[tuple[object, ...], ...]) -> None:
    conn.executemany(
        """
        INSERT INTO cor_entries (
            cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def build_test_settings(db_path, *, cor_local_db_path=None, nlp_enabled: bool = False) -> Settings:
    return Settings(
        environment="test",
        app_name="danote-backend-test",
        host="127.0.0.1",
        port=8001,
        db_path=db_path,
        nlp_model="retired-dacy-disabled",
        nlp_enabled=nlp_enabled,
        translation_enabled=False,
        cor_local_db_path=cor_local_db_path or (db_path.parent / "cor.sqlite"),
    )


def seed_cor_local_db(db_path) -> None:
    with sqlite3.connect(db_path) as conn:
        _create_cor_entries_table(conn)
        _insert_cor_entries(
            conn,
            (
                ("COR.30686.200.01", "lære", "learn", "vb.inf.akt", "lære", "N", 30686, 200, 1),
                ("COR.49032.110.01", "lærer", "teacher", "sb.fk.sg.ubest", "lærer", "N", 49032, 110, 1),
                ("COR.49032.112.01", "lærer", "teacher", "sb.fk.pl.ubest", "lærere", "N", 49032, 112, 1),
                ("COR.30686.203.01", "lære", "learn", "vb.præs.akt", "lærer", "N", 30686, 203, 1),
            ),
        )


def seed_cor_local_bog_senses(db_path) -> None:
    with sqlite3.connect(db_path) as conn:
        _create_cor_entries_table(conn)
        _insert_cor_entries(
            conn,
            (
                ("COR.BOG.BOOK.1", "bog", "book", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),
                ("COR.BOG.BOOK.2", "bog", "book", "sb.fk.pl.ubest", "bøger", "N", 123, 112, 1),
                ("COR.BOG.SWAMP.1", "bog", "swamp", "sb.fk.sg.best", "bogen", "N", 124, 211, 1),
                ("COR.BOG.SWAMP.2", "bog", "swamp", "sb.fk.pl.ubest", "moser", "N", 124, 212, 1),
            ),
        )


def seed_cor_local_word_page_gloss_cases(db_path) -> None:
    with sqlite3.connect(db_path) as conn:
        _create_cor_entries_table(conn)
        _insert_cor_entries(
            conn,
            (
                ("COR.BOG.READING.LEM", "bog", "til læsning", "sb.fk.sg.ubest", "bog", "N", 123, 110, 1),
                ("COR.BOG.READING.DEF", "bog", "til læsning", "sb.fk.sg.best", "bogen", "N", 123, 111, 1),
                ("COR.BOG.BEECHMAST.LEM", "bog", "frugt fra et bøgetræ", "sb.itk.sg.ubest", "bog", "N", 124, 110, 1),
                ("COR.BOG.BEECHMAST.DEF", "bog", "frugt fra et bøgetræ", "sb.itk.sg.best", "boget", "N", 124, 111, 1),
                ("COR.MOR.PERSON.LEM", "mor", "person", "sb.fk.sg.ubest", "mor", "N", 51046, 110, 1),
                ("COR.MOR.SOIL.LEM", "mor", "jordlag", "sb.fk.sg.ubest", "mor", "N", 51047, 110, 1),
            ),
        )

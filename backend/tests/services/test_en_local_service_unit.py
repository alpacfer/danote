from __future__ import annotations

import sqlite3
from pathlib import Path

from app.services.en_local import ENLocalLexiconService


def _create_en_local_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE en_entries (
                en_id TEXT PRIMARY KEY,
                lemma TEXT NOT NULL,
                lemma_lower TEXT NOT NULL,
                pos_raw TEXT NOT NULL,
                pos_ud TEXT NOT NULL,
                sense_idx INTEGER NOT NULL,
                gloss TEXT NOT NULL,
                examples_json TEXT,
                ipa TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE en_forms (
                form TEXT NOT NULL,
                form_lower TEXT NOT NULL,
                lemma TEXT NOT NULL,
                pos_ud TEXT NOT NULL,
                tags_json TEXT
            )
            """
        )


def test_en_local_service_returns_empty_results_when_db_is_missing(tmp_path: Path) -> None:
    service = ENLocalLexiconService(db_path=tmp_path / "missing.sqlite")

    assert service.has_form("book") is False
    assert service.lookup_form("book") == []
    assert service.lookup_lemma_senses("book") == []


def test_en_local_service_returns_empty_results_when_db_has_no_tables(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.sqlite"
    db_path.touch()
    service = ENLocalLexiconService(db_path=db_path)

    assert service.has_form("book") is False
    assert service.lookup_form("book") == []
    assert service.lookup_lemma_senses("book") == []


def test_lookup_form_prefers_best_inflected_match_per_pos_and_skips_pos_without_senses(tmp_path: Path) -> None:
    db_path = tmp_path / "english.sqlite"
    _create_en_local_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO en_entries (
                en_id, lemma, lemma_lower, pos_raw, pos_ud, sense_idx, gloss, examples_json, ipa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ("EN.book.NOUN.00", "book", "book", "noun", "NOUN", 0, "printed work", '["read the book"]', "/bʊk/"),
                ("EN.book.NOUN.01", "book", "book", "noun", "NOUN", 1, "set of sheets", "[]", "/bʊk/"),
                ("EN.book.VERB.00", "book", "book", "verb", "VERB", 0, "reserve in advance", "[]", "/bʊk/"),
            ),
        )
        conn.executemany(
            """
            INSERT INTO en_forms (form, form_lower, lemma, pos_ud, tags_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                ("books", "books", "book", "NOUN", "[]"),
                ("books", "books", "book", "NOUN", '["plural"]'),
                ("books", "books", "book", "VERB", '["third-person singular"]'),
                ("books", "books", "books", "PROPN", '["canonical"]'),
            ),
        )

    service = ENLocalLexiconService(db_path=db_path)

    matches = service.lookup_form("  BOOKS  ")

    assert [(item.lemma, item.pos_ud, item.tags) for item in matches] == [
        ("book", "NOUN", ["plural"]),
        ("book", "VERB", ["third-person singular"]),
    ]
    assert service.has_form("books") is True


def test_lookup_lemma_senses_handles_invalid_examples_json_and_pos_filter(tmp_path: Path) -> None:
    db_path = tmp_path / "english.sqlite"
    _create_en_local_db(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            """
            INSERT INTO en_entries (
                en_id, lemma, lemma_lower, pos_raw, pos_ud, sense_idx, gloss, examples_json, ipa
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ("EN.light.NOUN.00", "light", "light", "noun", "NOUN", 0, "illumination", '["turn on the light"]', ""),
                ("EN.light.NOUN.01", "light", "light", "noun", "NOUN", 1, "lamp", '{"oops": true}', None),
                ("EN.light.ADJ.00", "light", "light", "adjective", "ADJ", 0, "not heavy", '"not-a-list"', "/laɪt/"),
            ),
        )

    service = ENLocalLexiconService(db_path=db_path)

    noun_senses = service.lookup_lemma_senses("  light  ", "NOUN")
    all_senses = service.lookup_lemma_senses("light")

    assert [(item.sense_idx, item.gloss, item.examples, item.ipa) for item in noun_senses] == [
        (0, "illumination", ["turn on the light"], None),
        (1, "lamp", [], None),
    ]
    assert [(item.pos_ud, item.sense_idx) for item in all_senses] == [
        ("ADJ", 0),
        ("NOUN", 0),
        ("NOUN", 1),
    ]

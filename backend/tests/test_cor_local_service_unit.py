from __future__ import annotations

from pathlib import Path
import sqlite3

from app.services.cor_local import CORLocalLexiconService, decode_gram


def _create_cor_db(path: Path) -> None:
    with sqlite3.connect(path) as conn:
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
        conn.executemany(
            """
            INSERT INTO cor_entries (
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ("COR.49032.110.01", "lærer", "teacher", "sb.fk.sg.ubest", "lærer", "N", 49032, 110, 1),
                ("COR.49032.112.01", "lærer", "teacher", "sb.fk.pl.ubest", "lærere", "N", 49032, 112, 1),
                ("COR.30686.203.01", "lære", "learn", "vb.præs.akt", "lærer", "N", 30686, 203, 1),
                ("COR.49032.114.01", "lærer", "teacher", "sb.fk.sg.ubest.gen", "lærers", "K", 49032, 114, 1),
            ),
        )


def test_lookup_form_prefers_exact_then_case_insensitive_fallback(tmp_path: Path) -> None:
    db_path = tmp_path / "cor.sqlite"
    _create_cor_db(db_path)
    service = CORLocalLexiconService(db_path=db_path)

    exact = service.lookup_form("lærer")
    fallback = service.lookup_form("LÆRER")

    assert [item.cor_id for item in exact] == ["COR.30686.203.01", "COR.49032.110.01"]
    assert [item.cor_id for item in fallback] == ["COR.30686.203.01", "COR.49032.110.01"]


def test_lookup_lemma_returns_stable_norm_order(tmp_path: Path) -> None:
    db_path = tmp_path / "cor.sqlite"
    _create_cor_db(db_path)
    service = CORLocalLexiconService(db_path=db_path)

    entries = service.lookup_lemma(49032)

    assert [entry.cor_id for entry in entries] == [
        "COR.49032.110.01",
        "COR.49032.112.01",
        "COR.49032.114.01",
    ]
    assert entries[0].morphology == "Gender=Com|Number=Sing|Definite=Ind"
    assert entries[2].morphology == "Gender=Com|Number=Sing|Definite=Ind|Case=Gen"


def test_decode_gram_preserves_unknown_tags() -> None:
    pos_tag, morphology, features, extra_tags = decode_gram("vb.perf.part.sg.fk.xyz")

    assert pos_tag == "VERB"
    assert morphology == "Aspect=Perf|VerbForm=Part|Number=Sing|Gender=Com"
    assert features["Aspect"] == "Perf"
    assert features["VerbForm"] == "Part"
    assert extra_tags == ["xyz"]

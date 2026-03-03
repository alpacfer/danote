from __future__ import annotations

from pathlib import Path
import sqlite3

from app.services.cor_local_builder import build_cor_sqlite, parse_cor_id


def test_parse_cor_id_strict_validation() -> None:
    assert parse_cor_id("COR.49032.110.01") == (49032, 110, 1)
    assert parse_cor_id("COR.49032.11.01") is None
    assert parse_cor_id("XOR.49032.110.01") is None


def test_build_cor_sqlite_imports_valid_rows_and_skips_malformed(tmp_path: Path) -> None:
    input_path = tmp_path / "cor.tsv"
    output_path = tmp_path / "cor.sqlite"
    input_path.write_text(
        "\n".join(
            [
                "COR.49032.110.01\tlærer\tteacher\tsb.fk.sg.ubest\tlærer\tN",
                "COR.49032.112.01\tlærer\tteacher\tsb.fk.pl.ubest\tlærere\tN",
                "BROKEN.49032.112.01\tlærer\tteacher\tsb.fk.pl.ubest\tlærere\tN",
                "COR.49032.114.01\tlærer\tteacher\tsb.fk.sg.ubest.gen\tlærers",
                "\t\t\t\t\t",
            ]
        ),
        encoding="utf-8",
    )

    stats = build_cor_sqlite(input_path=input_path, output_path=output_path, batch_size=2)

    assert stats.total_rows == 5
    assert stats.inserted_rows == 2
    assert stats.skipped_rows == 3
    assert stats.malformed_id_rows == 1
    assert stats.malformed_column_rows == 1
    assert stats.missing_required_rows == 1

    with sqlite3.connect(output_path) as conn:
        row = conn.execute("SELECT COUNT(*) FROM cor_entries").fetchone()
        assert row is not None
        assert row[0] == 2

        indexes = conn.execute("PRAGMA index_list('cor_entries')").fetchall()
        index_names = {item[1] for item in indexes}
        assert "idx_cor_form" in index_names
        assert "idx_cor_form_lower" in index_names
        assert "idx_cor_lemma_idx" in index_names
        assert "idx_cor_lemma_gram" in index_names

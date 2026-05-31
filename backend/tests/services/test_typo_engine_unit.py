from __future__ import annotations

from app.db.migrations import apply_migrations, get_connection
from app.services.typo.typo_engine import TypoEngine


def _seed_lemma(db_path, lemma: str) -> None:
    with get_connection(db_path) as conn:
        conn.execute("INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')", (lemma,))


def test_typo_engine_flags_clear_typo_candidate(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    _seed_lemma(db_path, "spiser")
    dictionary_path = tmp_path / "da_words.txt"
    dictionary_path.write_text("spiser\nspise\n", encoding="utf-8")
    engine = TypoEngine(db_path=db_path, dictionary_path=dictionary_path)

    result = engine.classify_unknown(token="spisr")

    assert result.status == "typo_likely"
    assert result.suggestions
    assert result.suggestions[0].value in {"spiser", "spise"}


def test_typo_engine_skips_acronym_and_digits(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    dictionary_path = tmp_path / "da_words.txt"
    dictionary_path.write_text("sensor\n", encoding="utf-8")
    engine = TypoEngine(db_path=db_path, dictionary_path=dictionary_path)

    acronym = engine.classify_unknown(token="USB")
    digits = engine.classify_unknown(token="abc123")

    assert acronym.status == "new"
    assert "gating_skip_acronym" in acronym.reason_tags
    assert digits.status == "new"
    assert "gating_skip_digit_ratio" in digits.reason_tags


def test_typo_engine_uses_multiple_dictionaries(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    primary_dictionary_path = tmp_path / "da_words.txt"
    secondary_dictionary_path = tmp_path / "dsdo.txt"
    primary_dictionary_path.write_text("spise\n", encoding="utf-8")
    secondary_dictionary_path.write_text("abandonner\n", encoding="utf-8")
    engine = TypoEngine(
        db_path=db_path,
        dictionary_paths=(primary_dictionary_path, secondary_dictionary_path),
    )

    result = engine.classify_unknown(token="abandonenr")

    assert result.suggestions
    assert result.suggestions[0].value == "abandonner"


def test_typo_engine_updates_in_memory_ignored_cache_on_add(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    dictionary_path = tmp_path / "da_words.txt"
    dictionary_path.write_text("sensor\n", encoding="utf-8")
    engine = TypoEngine(db_path=db_path, dictionary_path=dictionary_path)

    engine.classify_unknown(token="sensro")
    engine.add_ignored_token("sensro")
    result = engine.classify_unknown(token="sensro")

    assert result.status == "new"
    assert "gating_skip_ignored" in result.reason_tags

from pathlib import Path

from app.db.migrations import apply_migrations
from app.db.repositories import WordbankRepository


def test_wordbank_repository_facade_exposes_read_and_mutation_methods(tmp_path: Path) -> None:
    db_path = tmp_path / "wordbank.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, inserted = repository.insert_or_load_lexeme(
        stored_lemma="bog",
        translation=None,
        provider=None,
        pos_tag="NOUN",
        morphology=None,
    )
    assert inserted is True
    assert repository.get_lexeme("bog") is not None
    assert repository.list_lemmas()
    assert lexeme_id > 0

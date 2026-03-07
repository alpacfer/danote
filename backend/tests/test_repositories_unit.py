from app.db.migrations import apply_migrations
from app.db.repositories import SentencebankRepository, WordbankRepository


def test_wordbank_repository_lists_and_searches_lemmas(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, inserted = repository.insert_or_load_lexeme(
        stored_lemma="bog",
        translation="book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    assert inserted is True
    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form="bogen",
        translation="the book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Sing",
    )

    lemmas = repository.list_lemmas()
    matches = repository.search_lemmas("bog", limit=8)
    details = repository.get_lexeme("bog")
    surface_forms = repository.list_surface_forms(lexeme_id)

    assert lemmas[0].lemma == "bog"
    assert matches[0].match_surface == "bogen"
    assert details is not None
    assert details.english_translation == "book"
    assert surface_forms[0].form == "bogen"


def test_sentencebank_repository_round_trips_sentences(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = SentencebankRepository(db_path)

    repository.insert_sentence(
        source_text="Jeg læser en bog",
        normalized_sentence="jeg læser en bog",
        english_translation="i read a book",
        translation_provider="stub",
    )

    existing = repository.find_by_normalized_sentence("jeg læser en bog")
    rows = repository.list_sentences()

    assert existing is not None
    assert existing.source_text == "Jeg læser en bog"
    assert rows[0].english_translation == "i read a book"

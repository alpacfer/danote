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


def test_wordbank_search_prefers_exact_then_prefix_then_translation(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    bog_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="bog",
        translation="book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=bog_id,
        form="bogen",
        translation="the book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Sing",
    )

    bogstav_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="bogstav",
        translation="letter",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=bogstav_id,
        form="bogstaver",
        translation="letters",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Plur",
    )

    house_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="hus",
        translation="bog house",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=house_id,
        form="huset",
        translation="the house",
        provider="stub",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Sing",
    )

    matches = repository.search_lemmas("bog", limit=8)

    assert [item.lemma for item in matches[:3]] == ["bog", "bogstav", "hus"]
    assert matches[0].match_surface == "bogen"
    assert matches[1].match_surface == "bogstaver"
    assert matches[2].match_surface is None


def test_wordbank_search_uses_prefix_only_for_short_queries(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="bog",
        translation="book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form="bogen",
        translation="the book",
        provider="stub",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Sing",
    )

    inside_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="xbog",
        translation="inside short search",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=inside_id,
        form="ubog",
        translation="inside short form",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )

    matches = repository.search_lemmas("bo", limit=8)

    assert [item.lemma for item in matches] == ["bog"]


def test_wordbank_search_uses_fts_for_longer_substring_queries(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="xbog",
        translation="inside substring search",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form="ubogens",
        translation="inside substring form",
        provider="stub",
        pos_tag="NOUN",
        morphology="Case=Gen|Number=Sing",
    )

    matches = repository.search_lemmas("bog", limit=8)

    assert [item.lemma for item in matches] == ["xbog"]
    assert matches[0].match_surface == "ubogens"


def test_wordbank_search_fts_stays_in_sync_with_lexeme_and_surface_updates(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="hus",
        translation="house",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    assert [item.lemma for item in repository.search_lemmas("hou", limit=8)] == ["hus"]

    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form="husene",
        translation="houses",
        provider="stub",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Plur",
    )
    surface_matches = repository.search_lemmas("sen", limit=8)
    assert [item.lemma for item in surface_matches] == ["hus"]
    assert surface_matches[0].match_surface == "husene"


def test_wordbank_repository_search_returns_query_cor_ids_for_exact_form(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, _ = repository.insert_or_load_lexeme(
        stored_lemma="lærer",
        translation="teacher",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )
    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        form="lærer",
        translation="teacher",
        provider="stub",
        pos_tag="NOUN",
        morphology="Number=Sing",
    )

    assert repository.insert_surface_form_cor_variant(
        lexeme_id=lexeme_id,
        form="lærer",
        cor_id="COR.49032.110.01",
    ) is True
    assert repository.insert_surface_form_cor_variant(
        lexeme_id=lexeme_id,
        form="lærer",
        cor_id="COR.49032.112.01",
    ) is True
    assert repository.insert_surface_form_cor_variant(
        lexeme_id=lexeme_id,
        form="lærer",
        cor_id="COR.49032.112.01",
    ) is False

    matches = repository.search_lemmas("lærer", limit=8)

    assert [item.lemma for item in matches] == ["lærer"]
    assert matches[0].query_cor_ids == ["COR.49032.110.01", "COR.49032.112.01"]


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

from app.db.migrations import apply_migrations
from app.db.repositories import SentencebankRepository, WordbankRepository


def _insert_meaning_scoped_lemma(
    repository: WordbankRepository,
    *,
    lemma: str,
    meaning_key: str,
    cor_lemma_idx: int | None,
    english_translation: str,
    pos_tag: str = "NOUN",
    morphology: str = "Number=Sing",
    forms: list[tuple[str, str | None]] | None = None,
) -> tuple[int, int]:
    lexeme_id, _inserted = repository.insert_or_load_lexeme(
        stored_lemma=lemma,
        translation=None,
        provider=None,
        pos_tag=pos_tag,
        morphology=morphology,
    )
    meaning, _meaning_inserted = repository.upsert_lexeme_meaning(
        lexeme_id=lexeme_id,
        meaning_key=meaning_key,
        cor_lemma_idx=cor_lemma_idx,
        gloss=meaning_key,
        english_translation=english_translation,
        pos_tag=pos_tag,
        morphology=morphology,
    )
    for form, form_morphology in forms or [
        (lemma, morphology),
    ]:
        repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=meaning.id,
            form=form,
            pos_tag=pos_tag,
            morphology=form_morphology or morphology,
        )
    return lexeme_id, meaning.id


def _insert_unsectioned_lemma(
    repository: WordbankRepository,
    *,
    lemma: str,
    english_translation: str,
    pos_tag: str = "VERB",
    morphology: str = "VerbForm=Inf",
    forms: list[tuple[str, str | None]] | None = None,
) -> int:
    lexeme_id, _inserted = repository.insert_or_load_lexeme(
        stored_lemma=lemma,
        translation=english_translation,
        provider="stub",
        pos_tag=pos_tag,
        morphology=morphology,
    )
    for form, form_morphology in forms or [
        (lemma, morphology),
    ]:
        repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=None,
            form=form,
            pos_tag=pos_tag,
            morphology=form_morphology or morphology,
        )
    return lexeme_id


def test_wordbank_repository_lists_and_searches_lemmas(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, meaning_id = _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="book",
        cor_lemma_idx=101,
        english_translation="book",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )

    lemmas = repository.list_lemmas()
    matches = repository.search_lemmas("bog", limit=8)
    details = repository.get_lexeme("bog")
    surface_forms = repository.list_surface_forms(lexeme_id)

    assert lemmas == [
        type(lemmas[0])(
            lemma="bog",
            english_translation="book",
            pos_tag="NOUN",
            variation_count=1,
        )
    ]
    assert [item.lemma for item in matches] == ["bog"]
    assert matches[0].meaning_id == meaning_id
    assert matches[0].meaning_key == "book"
    assert matches[0].match_surface == "bog"
    assert details is not None
    assert details.english_translation is None
    assert [(item.form, item.meaning_id) for item in surface_forms] == [("bog", meaning_id), ("bogen", meaning_id)]


def test_wordbank_search_prefers_exact_then_prefix_then_translation(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="book",
        cor_lemma_idx=101,
        english_translation="book",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )
    _insert_meaning_scoped_lemma(
        repository,
        lemma="bogstav",
        meaning_key="letter",
        cor_lemma_idx=102,
        english_translation="letter",
        forms=[
            ("bogstav", "Number=Sing"),
            ("bogstaver", "Number=Plur"),
        ],
    )
    _insert_unsectioned_lemma(
        repository,
        lemma="hus",
        english_translation="bog house",
        pos_tag="NOUN",
        morphology="Number=Sing",
        forms=[
            ("hus", "Number=Sing"),
            ("huset", "Definite=Def|Number=Sing"),
        ],
    )

    matches = repository.search_lemmas("bog", limit=8)

    assert [item.lemma for item in matches[:3]] == ["bog", "bogstav", "hus"]
    assert matches[0].match_surface == "bog"
    assert matches[1].match_surface == "bogstav"
    assert matches[2].match_surface is None


def test_wordbank_search_uses_prefix_only_for_short_queries(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="book",
        cor_lemma_idx=101,
        english_translation="book",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )
    _insert_meaning_scoped_lemma(
        repository,
        lemma="xbog",
        meaning_key="inside short search",
        cor_lemma_idx=102,
        english_translation="inside short search",
        forms=[
            ("xbog", "Number=Sing"),
            ("ubog", "Number=Sing"),
        ],
    )

    matches = repository.search_lemmas("bo", limit=8)

    assert [item.lemma for item in matches] == ["bog"]


def test_wordbank_search_uses_contains_for_longer_substring_queries(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    _insert_meaning_scoped_lemma(
        repository,
        lemma="xbog",
        meaning_key="inside substring search",
        cor_lemma_idx=102,
        english_translation="inside substring search",
        forms=[
            ("xbog", "Number=Sing"),
            ("ubogens", "Case=Gen|Number=Sing"),
        ],
    )

    matches = repository.search_lemmas("bog", limit=8)

    assert [item.lemma for item in matches] == ["xbog"]
    assert matches[0].match_surface == "ubogens"


def test_wordbank_search_stays_in_sync_with_lexeme_and_surface_updates(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id = _insert_unsectioned_lemma(
        repository,
        lemma="hus",
        english_translation="house",
        pos_tag="NOUN",
        morphology="Number=Sing",
        forms=[("hus", "Number=Sing")],
    )
    assert [item.lemma for item in repository.search_lemmas("hou", limit=8)] == ["hus"]

    repository.insert_or_update_surface_form(
        lexeme_id=lexeme_id,
        meaning_id=None,
        form="husene",
        pos_tag="NOUN",
        morphology="Definite=Def|Number=Plur",
    )
    surface_matches = repository.search_lemmas("sen", limit=8)
    assert [item.lemma for item in surface_matches] == ["hus"]
    assert surface_matches[0].match_surface == "husene"


def test_wordbank_repository_search_returns_query_cor_ids_per_meaning(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    lexeme_id, book_meaning_id = _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="book",
        cor_lemma_idx=101,
        english_translation="book",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )
    _lexeme_id, swamp_meaning_id = _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="swamp",
        cor_lemma_idx=202,
        english_translation="swamp",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )

    book_surface = next(
        row for row in repository.find_surface_forms(lexeme_id=lexeme_id, form="bogen") if row.meaning_id == book_meaning_id
    )
    swamp_surface = next(
        row for row in repository.find_surface_forms(lexeme_id=lexeme_id, form="bogen") if row.meaning_id == swamp_meaning_id
    )

    assert repository.insert_surface_form_cor_variant(
        surface_form_id=book_surface.id,
        cor_id="COR.BOG.BOOK.1",
    ) is True
    assert repository.insert_surface_form_cor_variant(
        surface_form_id=swamp_surface.id,
        cor_id="COR.BOG.SWAMP.1",
    ) is True
    assert repository.insert_surface_form_cor_variant(
        surface_form_id=swamp_surface.id,
        cor_id="COR.BOG.SWAMP.1",
    ) is False

    matches = repository.search_lemmas("bogen", limit=8)

    assert [(item.meaning_key, item.query_cor_ids) for item in matches] == [
        ("book", ["COR.BOG.BOOK.1"]),
        ("swamp", ["COR.BOG.SWAMP.1"]),
    ]


def test_wordbank_repository_search_returns_two_rows_for_exact_homograph_lemma(tmp_path) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    repository = WordbankRepository(db_path)

    _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="book",
        cor_lemma_idx=101,
        english_translation="book",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )
    _insert_meaning_scoped_lemma(
        repository,
        lemma="bog",
        meaning_key="swamp",
        cor_lemma_idx=202,
        english_translation="swamp",
        forms=[
            ("bog", "Number=Sing"),
            ("bogen", "Definite=Def|Number=Sing"),
        ],
    )

    matches = repository.search_lemmas("bog", limit=8)

    assert [(item.meaning_key, item.match_surface) for item in matches] == [
        ("book", "bog"),
        ("swamp", "bog"),
    ]


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

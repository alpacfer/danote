from __future__ import annotations

from pathlib import Path

from app.db.migrations import apply_migrations
from app.services.cor_local import CORLocalEntry
from tests.helpers.fakes import FakeCORLocalLexiconService


def _cor_local_entry(
    *,
    cor_id: str,
    lemma: str,
    gloss: str | None,
    form: str,
    lemma_idx: int,
    pos_tag: str,
    morphology: str,
    gram_raw: str = "",
) -> CORLocalEntry:
    return CORLocalEntry(
        cor_id=cor_id,
        lemma=lemma,
        gloss=gloss,
        gram_raw=gram_raw,
        form=form,
        norm="N",
        lemma_idx=lemma_idx,
        gram_code=0,
        variation=0,
        pos_tag=pos_tag,
        morphology=morphology,
        features={},
        extra_tags=[],
    )


def _db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    return db_path


def _bog_homograph_cor_local() -> FakeCORLocalLexiconService:
    book_lemma = _cor_local_entry(
        cor_id="COR.BOG.BOOK.LEM",
        lemma="bog",
        gloss="book",
        form="bog",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    book_surface = _cor_local_entry(
        cor_id="COR.BOG.BOOK.DEF",
        lemma="bog",
        gloss="book",
        form="bogen",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    book_plural = _cor_local_entry(
        cor_id="COR.BOG.BOOK.PL",
        lemma="bog",
        gloss="book",
        form="bøger",
        lemma_idx=123,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    swamp_lemma = _cor_local_entry(
        cor_id="COR.BOG.SWAMP.LEM",
        lemma="bog",
        gloss="swamp",
        form="bog",
        lemma_idx=124,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Ind",
        gram_raw="sb.fk.sg.ubest",
    )
    swamp_surface = _cor_local_entry(
        cor_id="COR.BOG.SWAMP.DEF",
        lemma="bog",
        gloss="swamp",
        form="bogen",
        lemma_idx=124,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Sing|Definite=Def",
        gram_raw="sb.fk.sg.best",
    )
    swamp_plural = _cor_local_entry(
        cor_id="COR.BOG.SWAMP.PL",
        lemma="bog",
        gloss="swamp",
        form="moser",
        lemma_idx=124,
        pos_tag="NOUN",
        morphology="Gender=Com|Number=Plur|Definite=Ind",
        gram_raw="sb.fk.pl.ubest",
    )
    return FakeCORLocalLexiconService(
        by_form={
            "bog": [book_lemma, swamp_lemma],
            "bogen": [book_surface, swamp_surface],
            "bøger": [book_plural],
            "moser": [swamp_plural],
        },
        by_lemma_idx={
            123: [book_lemma, book_surface, book_plural],
            124: [swamp_lemma, swamp_surface, swamp_plural],
        },
    )

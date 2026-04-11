from __future__ import annotations

from pathlib import Path

from app.nlp.adapter import NLPToken
from app.services.use_cases.analyze import AnalyzeNoteUseCase, strip_inline_comments
from tests.helpers.factories import _db_path
from tests.helpers.fakes import (
    FakeNLPAdapter,
)


def test_analyze_use_case_propagates_pos_and_morphology(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
    )

    tokens = use_case.execute("Hej bog")

    assert tokens[0].surface_token == "Hej"
    assert tokens[0].pos_tag == "INTJ"
    assert tokens[0].morphology == "PronType=Prs"
    assert tokens[1].surface_token == "bog"
    assert tokens[1].pos_tag == "NOUN"
    assert tokens[1].morphology == "Definite=Ind|Gender=Com"

def test_analyze_use_case_skips_short_letter_words(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
    )

    tokens = use_case.execute("i to hej bog")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["Hej", "bog"]

def test_analyze_use_case_filters_non_word_tokens(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
    )

    tokens = use_case.execute("Hej, bog")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["Hej", "bog"]

def test_analyze_use_case_includes_pos_and_morphology(tmp_path: Path) -> None:
    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=FakeNLPAdapter(),
    )

    tokens = use_case.execute("Hej, bog")
    assert tokens[0].pos_tag == "INTJ"
    assert tokens[0].morphology == "PronType=Prs"
    assert tokens[1].pos_tag == "NOUN"
    assert tokens[1].morphology == "Definite=Ind|Gender=Com"

def test_strip_inline_comments_removes_text_after_hash_per_line() -> None:
    text = "hej # ignore this\nverden\n# full line comment\nigen # skip"
    stripped = strip_inline_comments(text)
    assert stripped == "hej \nverden\n\nigen "

def test_analyze_use_case_ignores_comment_text_after_hash(tmp_path: Path) -> None:
    class WhitespaceNLPAdapter:
        def tokenize(self, text: str) -> list[NLPToken]:
            return [
                NLPToken(
                    text=part,
                    lemma=part.lower(),
                    pos="X",
                    morphology=None,
                    is_punctuation=False,
                )
                for part in text.split()
            ]

        def lemma_candidates_for_token(self, token: str) -> list[str]:
            return [token.lower()]

        def lemma_for_token(self, token: str) -> str | None:
            return token.lower()

        def metadata(self) -> dict[str, str]:
            return {"adapter": "whitespace-fake"}

    use_case = AnalyzeNoteUseCase(
        _db_path(tmp_path),
        nlp_adapter=WhitespaceNLPAdapter(),
    )

    tokens = use_case.execute("hej # ignore me\nverden")
    surfaces = [token.surface_token for token in tokens]
    assert surfaces == ["hej", "verden"]


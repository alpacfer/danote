from __future__ import annotations

from pathlib import Path

from app.db.migrations import apply_migrations, get_connection
from app.services.token_classifier import LemmaAwareClassifier
from app.services.typo.typo_engine import TypoEngine


class _FixtureNLPAdapter:
    def __init__(self) -> None:
        self._lemma_overrides = {
            "bogen": ["bog"],
        }

    def tokenize(self, text: str):
        return []

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        normalized = token.lower()
        return self._lemma_overrides.get(normalized, [normalized])

    def lemma_for_token(self, token: str) -> str | None:
        candidates = self.lemma_candidates_for_token(token)
        return candidates[0] if candidates else None

    def metadata(self) -> dict[str, str]:
        return {"adapter": "fixture_stub"}


def _seed_lexemes(db_path: Path, lemmas: list[str]) -> None:
    with get_connection(db_path) as conn:
        for lemma in lemmas:
            conn.execute(
                "INSERT OR IGNORE INTO lexemes (lemma, source) VALUES (?, 'manual')",
                (lemma.lower(),),
            )


def _build_engine(tmp_path: Path, *, lemmas: list[str], dictionary_words: list[str]) -> TypoEngine:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    _seed_lexemes(db_path, lemmas)
    dictionary_path = tmp_path / "da_words.txt"
    dictionary_path.write_text("\n".join(dictionary_words) + "\n", encoding="utf-8")
    return TypoEngine(db_path=db_path, dictionary_path=dictionary_path)


def test_typo_detection_end_to_end_with_classifier_precedence_and_guards(tmp_path) -> None:
    engine = _build_engine(
        tmp_path,
        lemmas=["bog", "spise", "sensor"],
        dictionary_words=["bog", "spise", "spiser", "sensor"],
    )
    classifier = LemmaAwareClassifier(
        tmp_path / "danote.sqlite3",
        nlp_adapter=_FixtureNLPAdapter(),
        typo_engine=engine,
    )

    # Exact and lemma-variation precedence should short-circuit typo checks.
    known = classifier.classify("bog")
    variation = classifier.classify("bogen")
    assert known.classification == "known"
    assert "exact_match" in known.reason_tags
    assert variation.classification == "variation"
    assert "lemma_match" in variation.reason_tags

    # Genuine misspelling should be sent to typo engine and produce suggestions.
    typo = classifier.classify("spisr")
    assert typo.classification in {"typo_likely", "uncertain"}
    assert typo.suggestions
    assert typo.suggestions[0].value in {"spiser", "spise"}

    # Acronym and digit-ratio guards should skip typo evaluation.
    acronym = classifier.classify("PLC")
    mixed = classifier.classify("usb6525")
    assert acronym.classification == "new"
    assert "gating_skip_acronym" in acronym.reason_tags
    assert mixed.classification == "new"
    assert "gating_skip_digit_ratio" in mixed.reason_tags


def test_typo_engine_cache_ignore_and_feedback_logging(tmp_path) -> None:
    engine = _build_engine(
        tmp_path,
        lemmas=["spise", "klasse"],
        dictionary_words=["spise", "spiser", "klasse"],
    )
    db_path = tmp_path / "danote.sqlite3"

    first = engine.classify_unknown(token="spisr")
    second = engine.classify_unknown(token="spisr")

    # Second call should hit cache and return exactly the same immutable result object.
    assert first is second

    with get_connection(db_path) as conn:
        events_before_ignore = conn.execute(
            "SELECT COUNT(*) AS c FROM token_events WHERE raw_token = 'spisr'"
        ).fetchone()["c"]
    assert events_before_ignore == 1

    engine.add_ignored_token("spisr")
    ignored = engine.classify_unknown(token="spisr")
    assert ignored.status == "new"
    assert ignored.suggestions == ()
    assert "gating_skip_ignored" in ignored.reason_tags

    with get_connection(db_path) as conn:
        events_after_ignore = conn.execute(
            "SELECT COUNT(*) AS c FROM token_events WHERE raw_token = 'spisr'"
        ).fetchone()["c"]
    assert events_after_ignore == 2

    engine.add_feedback(
        raw_token="spisr",
        predicted_status=first.status,
        suggestions_shown=[item.value for item in first.suggestions],
        user_action="replace",
        chosen_value="spiser",
    )

    with get_connection(db_path) as conn:
        row = conn.execute(
            "SELECT raw_token, predicted_status, user_action, chosen_value FROM typo_feedback"
        ).fetchone()
    assert row["raw_token"] == "spisr"
    assert row["predicted_status"] == first.status
    assert row["user_action"] == "replace"
    assert row["chosen_value"] == "spiser"


def test_typo_engine_proper_noun_bias_is_applied_only_off_sentence_start(tmp_path) -> None:
    engine = _build_engine(
        tmp_path,
        lemmas=["møde", "klasse"],
        dictionary_words=["møde", "klasse", "milkoscna"],
    )

    sentence_start = engine.classify_unknown(token="MilkoScna", sentence_start=True)
    mid_sentence = engine.classify_unknown(token="MilkoScna", sentence_start=False)

    # Same token, but only the non-initial position should carry proper-noun bias.
    assert "proper_noun_bias" not in sentence_start.reason_tags
    assert "proper_noun_bias" in mid_sentence.reason_tags
    assert mid_sentence.status in {"new", "uncertain"}

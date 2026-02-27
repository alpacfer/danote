from __future__ import annotations

import pytest

from app.db.migrations import apply_migrations
from app.db.seed import seed_starter_data
from app.nlp.danish import DaCyLemmyNLPAdapter
from app.services.token_classifier import LemmaAwareClassifier


MODEL = "da_dacy_small_trf-0.2.0"


@pytest.fixture(scope="module")
def real_adapter() -> DaCyLemmyNLPAdapter:
    return DaCyLemmyNLPAdapter(MODEL)


def test_service_db_end_to_end_single_token(tmp_path, real_adapter: DaCyLemmyNLPAdapter) -> None:
    db_path = tmp_path / "danote.sqlite3"
    apply_migrations(db_path)
    seed_starter_data(db_path)

    classifier = LemmaAwareClassifier(db_path, nlp_adapter=real_adapter)

    known = classifier.classify("bog")
    variation = classifier.classify("bogen")
    unknown = classifier.classify("kat")
    known_case_variant = classifier.classify("  BOG ")
    punctuation = classifier.classify("!!!")

    assert known.classification == "known"
    assert known.match_source == "exact"
    assert known.matched_lemma == "bog"

    assert variation.classification == "variation"
    assert variation.match_source == "lemma"
    assert variation.lemma_candidate == "bog"

    assert unknown.classification == "new"
    assert unknown.match_source == "none"
    assert unknown.matched_lemma is None

    assert known_case_variant.classification == "known"
    assert known_case_variant.normalized_token == "bog"

    assert punctuation.classification == "new"

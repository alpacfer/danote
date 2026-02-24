from __future__ import annotations

import pytest

from app.nlp.danish import DaCyLemmyNLPAdapter


MODEL = "da_dacy_small_tft-0.0.0"


@pytest.fixture(scope="module")
def real_adapter() -> DaCyLemmyNLPAdapter:
    return DaCyLemmyNLPAdapter(MODEL)


def test_real_nlp_bogen_lemmatizes_to_bog(real_adapter: DaCyLemmyNLPAdapter) -> None:
    adapter = real_adapter
    assert adapter.lemma_for_token("bogen") == "bog"


def test_real_nlp_handles_punctuation_only_safely(
    real_adapter: DaCyLemmyNLPAdapter,
) -> None:
    adapter = real_adapter
    assert adapter.lemma_for_token("!!!") is None


def test_real_nlp_handles_empty_input_safely(real_adapter: DaCyLemmyNLPAdapter) -> None:
    adapter = real_adapter
    assert adapter.tokenize("   ") == []

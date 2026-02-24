from __future__ import annotations

import sys
import types

from app.nlp.danish import DaCyLemmyNLPAdapter


class _FakeToken:
    def __init__(self, text: str, tag_: str, is_punct: bool = False):
        self.text = text
        self.tag_ = tag_
        self.pos_ = ""
        self.is_punct = is_punct
        self.is_space = False
        self.morph = ""


class _FakeNLP:
    def __init__(self):
        self.meta = {"spacy_version": ">=3.0.0,<4.0.0"}

    def __call__(self, text: str):
        mapping = {
            "bogen": [_FakeToken("bogen", "NOUN")],
            "kan": [_FakeToken("kan", "VERB")],
            "hus": [_FakeToken("hus", "NOUN")],
            "husets": [_FakeToken("husets", "X")],
            "spist": [_FakeToken("spist", "X")],
            "gået": [_FakeToken("gået", "X")],
            "lærer": [_FakeToken("lærer", "NOUN")],
        }
        if text in mapping:
            return mapping[text]
        return [_FakeToken(text, "X", is_punct=not text.isalpha())]


class _FakeLemmy:
    def lemmatize(self, word_class: str, full_form: str):
        table = {
            ("NOUN", "bogen"): ["bog"],
            ("VERB", "kan"): ["kunne"],
            ("NOUN", "hus"): ["hu", "hus"],
            ("X", "husets"): ["husets"],
            ("X", "spist"): ["spist"],
            ("X", "gået"): ["gået"],
            ("NOUN", "lærer"): ["lærer", "lære"],
            ("", "hus"): ["hus", "hu", "huse"],
            ("", "husets"): ["hus"],
            ("", "spist"): ["spise"],
            ("", "gået"): ["gå"],
            ("", "lærer"): ["lære", "lærer"],
        }
        return table.get((word_class, full_form), [full_form])


def test_adapter_returns_lemmas_for_simple_danish_nouns_verbs(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "dacy", types.SimpleNamespace(load=lambda _model: _FakeNLP()))
    monkeypatch.setitem(sys.modules, "lemmy", types.SimpleNamespace(load=lambda _lang: _FakeLemmy()))

    adapter = DaCyLemmyNLPAdapter("fake-model")

    assert adapter.lemma_for_token("bogen") == "bog"
    assert adapter.lemma_for_token("kan") == "kunne"


def test_adapter_candidate_ranking_handles_common_failure_patterns(monkeypatch) -> None:
    monkeypatch.setitem(sys.modules, "dacy", types.SimpleNamespace(load=lambda _model: _FakeNLP()))
    monkeypatch.setitem(sys.modules, "lemmy", types.SimpleNamespace(load=lambda _lang: _FakeLemmy()))

    adapter = DaCyLemmyNLPAdapter("fake-model")

    assert adapter.lemma_for_token("hus") == "hus"
    assert adapter.lemma_for_token("husets") == "hus"
    assert adapter.lemma_for_token("spist") == "spise"
    assert adapter.lemma_for_token("gået") == "gå"
    assert adapter.lemma_for_token("lærer") == "lære"

from __future__ import annotations

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
    def __call__(self, text: str):
        mapping = {
            "bogen": [_FakeToken("bogen", "NOUN")],
            "kan": [_FakeToken("kan", "VERB")],
        }
        if text in mapping:
            return mapping[text]
        return [_FakeToken(text, "X", is_punct=not text.isalpha())]


class _FakeLemmy:
    def lemmatize(self, word_class: str, full_form: str):
        table = {
            ("NOUN", "bogen"): ["bog"],
            ("VERB", "kan"): ["kunne"],
        }
        return table.get((word_class, full_form), [full_form])


def test_adapter_returns_lemmas_for_simple_danish_nouns_verbs(monkeypatch) -> None:
    monkeypatch.setattr("app.nlp.danish.dacy.load", lambda _model: _FakeNLP())
    monkeypatch.setattr("app.nlp.danish.lemmy.load", lambda _lang: _FakeLemmy())

    adapter = DaCyLemmyNLPAdapter("fake-model")

    assert adapter.lemma_for_token("bogen") == "bog"
    assert adapter.lemma_for_token("kan") == "kunne"

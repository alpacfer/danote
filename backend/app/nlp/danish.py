from __future__ import annotations

from importlib.metadata import version

import dacy
import lemmy

from app.core.config import Settings
from app.nlp.adapter import NLPAdapter, NLPToken


class DaCyLemmyNLPAdapter(NLPAdapter):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._nlp = dacy.load(model_name)
        self._lemmatizer = lemmy.load("da")

    def tokenize(self, text: str) -> list[NLPToken]:
        if not text.strip():
            return []

        doc = self._nlp(text)
        return [self._to_nlp_token(token) for token in doc if not token.is_space]

    def lemma_for_token(self, token: str) -> str | None:
        cleaned = token.strip()
        if not cleaned:
            return None

        doc = self._nlp(cleaned)
        for spacy_token in doc:
            if spacy_token.is_space or spacy_token.is_punct:
                continue
            return self._lemma_from_token(spacy_token)
        return None

    def metadata(self) -> dict[str, str]:
        return {
            "adapter": self.__class__.__name__,
            "dacy": version("dacy"),
            "spacy": version("spacy"),
            "lemmy": version("lemmy"),
            "model": self.model_name,
        }

    def _to_nlp_token(self, token) -> NLPToken:
        pos = token.pos_ or token.tag_ or None
        morph = str(token.morph) if str(token.morph) else None
        lemma = None if token.is_punct else self._lemma_from_token(token)
        return NLPToken(
            text=token.text,
            lemma=lemma,
            pos=pos,
            morphology=morph,
            is_punctuation=bool(token.is_punct),
        )

    def _lemma_from_token(self, token) -> str | None:
        word_class = token.pos_ or token.tag_ or "X"
        lemmas = self._lemmatizer.lemmatize(word_class, token.text.lower())
        if not lemmas:
            return None
        return lemmas[0]


def load_danish_nlp_adapter(settings: Settings) -> NLPAdapter:
    return DaCyLemmyNLPAdapter(model_name=settings.nlp_model)

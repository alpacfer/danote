from __future__ import annotations

import logging
from importlib.metadata import version as package_version

from packaging.specifiers import SpecifierSet
from packaging.version import InvalidVersion, Version

from app.core.config import Settings
from app.nlp.adapter import NLPAdapter, NLPToken
from app.nlp.lemma_candidate_ranker import (
    merge_candidates,
    pick_best_candidate,
    rank_candidates,
)


logger = logging.getLogger(__name__)


class DaCyLemmyNLPAdapter(NLPAdapter):
    def __init__(self, model_name: str):
        self.model_name = model_name
        # Import lazily so backend startup can degrade cleanly if NLP deps are absent.
        import dacy
        import lemmy

        self._nlp = dacy.load(model_name)
        self._lemmatizer = lemmy.load("da")
        self._warn_if_spacy_version_incompatible()

    def tokenize(self, text: str) -> list[NLPToken]:
        if not text.strip():
            return []

        doc = self._nlp(text)
        return [self._to_nlp_token(token) for token in doc if not token.is_space]

    def lemma_for_token(self, token: str) -> str | None:
        candidates = self.lemma_candidates_for_token(token)
        return candidates[0] if candidates else None

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        cleaned = token.strip()
        if not cleaned:
            return []

        doc = self._nlp(cleaned)
        for spacy_token in doc:
            if spacy_token.is_space or spacy_token.is_punct:
                continue
            return self._lemma_candidates_from_token(spacy_token)
        return []

    def metadata(self) -> dict[str, str]:
        return {
            "adapter": self.__class__.__name__,
            "dacy": package_version("dacy"),
            "spacy": package_version("spacy"),
            "lemmy": package_version("lemmy"),
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

    def _lemma_candidates_from_token(self, token) -> list[str]:
        word_class = token.pos_ or token.tag_ or "X"
        normalized_text = token.text.lower()
        primary_candidates = self._lemmatizer.lemmatize(word_class, normalized_text)
        fallback_candidates = self._lemmatizer.lemmatize("", normalized_text)
        merged = merge_candidates(primary_candidates, fallback_candidates)
        return rank_candidates(
            surface=token.text,
            tag=word_class,
            candidates=merged,
            primary_tag_candidates=primary_candidates,
        )

    def _warn_if_spacy_version_incompatible(self) -> None:
        runtime_version_str = package_version("spacy")
        model_spec = str(self._nlp.meta.get("spacy_version") or "").strip()
        if not model_spec:
            return

        try:
            runtime_version = Version(runtime_version_str)
            compat_spec = SpecifierSet(model_spec)
        except InvalidVersion:
            logger.warning(
                "nlp_spacy_version_parse_failed",
                extra={
                    "model": self.model_name,
                    "runtime_spacy": runtime_version_str,
                    "model_spacy_spec": model_spec,
                },
            )
            return

        if compat_spec.contains(runtime_version, prereleases=True):
            return

        logger.warning(
            "nlp_model_spacy_version_mismatch",
            extra={
                "model": self.model_name,
                "runtime_spacy": runtime_version_str,
                "model_spacy_spec": model_spec,
            },
        )

    def _lemma_from_token(self, token) -> str | None:
        word_class = token.pos_ or token.tag_ or "X"
        primary_candidates = self._lemmatizer.lemmatize(word_class, token.text.lower())
        fallback_candidates = self._lemmatizer.lemmatize("", token.text.lower())
        return pick_best_candidate(
            surface=token.text,
            tag=word_class,
            primary_tag_candidates=primary_candidates,
            fallback_candidates=fallback_candidates,
        )


def load_danish_nlp_adapter(settings: Settings) -> NLPAdapter:
    return DaCyLemmyNLPAdapter(model_name=settings.nlp_model)

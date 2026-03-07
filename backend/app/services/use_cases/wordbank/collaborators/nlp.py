from __future__ import annotations

from app.nlp.token_filter import is_wordlike_token
from app.services.cor import COREntry, CORLexiconService
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.shared import _cor_entry_priority


class NLPCollaborator:
    """Owns NLP-based POS/morphology extraction and the associated cache."""

    def __init__(
        self,
        nlp_adapter,
        typo_engine,
        cor_lexicon_service: CORLexiconService | None = None,
    ) -> None:
        self._nlp_adapter = nlp_adapter
        self._typo_engine = typo_engine
        self._cor_lexicon_service = cor_lexicon_service
        self._pos_morph_cache: dict[tuple[str, str | None], tuple[str | None, str | None]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_pos_and_morphology(
        self,
        value: str,
        *,
        preferred_pos_tag: str | None = None,
    ) -> tuple[str | None, str | None]:
        normalized_value = normalize_token(value)
        normalized_preferred_pos = self.normalize_optional_pos_tag(preferred_pos_tag)
        cache_key = (normalized_value, normalized_preferred_pos)
        cached = self._pos_morph_cache.get(cache_key)
        if cached is not None:
            return cached

        entries = self._cor_entries_for_surface(normalized_value)
        cor_entry = self._best_cor_entry(
            entries,
            normalized_surface=normalized_value,
            preferred_pos_tag=normalized_preferred_pos,
        )
        if cor_entry is not None:
            extracted = (cor_entry.pos_tag, cor_entry.morphology)
            self._pos_morph_cache[cache_key] = extracted
            return extracted

        if self._nlp_adapter is None:
            self._pos_morph_cache[cache_key] = (None, None)
            return None, None

        for token in self._nlp_adapter.tokenize(normalized_value):
            surface = token.text
            if not surface.strip():
                continue
            if token.is_punctuation:
                continue
            if not is_wordlike_token(surface):
                continue
            extracted = (token.pos, token.morphology)
            self._pos_morph_cache[cache_key] = extracted
            return extracted

        self._pos_morph_cache[cache_key] = (None, None)
        return None, None

    def extract_pos_and_morphology_batch(
        self, values: list[str]
    ) -> dict[str, tuple[str | None, str | None]]:
        return {value: self.extract_pos_and_morphology(value) for value in values}

    def invalidate_pos_cache(self, lemma: str, surface: str | None) -> None:
        values = {normalize_token(lemma)}
        if surface:
            values.add(normalize_token(surface))
        keys_to_delete = [key for key in self._pos_morph_cache if key[0] in values]
        for key in keys_to_delete:
            self._pos_morph_cache.pop(key, None)

    def invalidate_typo_cache(self) -> None:
        if self._typo_engine is not None:
            self._typo_engine.invalidate_cache()

    def add_user_lexeme(self, lemma: str) -> None:
        if self._typo_engine is not None:
            self._typo_engine.add_user_lexeme(lemma)

    @property
    def typo_engine(self):
        return self._typo_engine

    @staticmethod
    def normalize_optional_pos_tag(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip().upper()
        if not cleaned:
            return None
        return cleaned

    @staticmethod
    def normalize_optional_morphology(value: str | None) -> str | None:
        if not isinstance(value, str):
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        return cleaned

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _cor_entries_for_surface(self, normalized_value: str) -> list[COREntry]:
        if self._cor_lexicon_service is None:
            return []
        return self._cor_lexicon_service.lookup_full_form(normalized_value)

    def _best_cor_entry(
        self,
        entries: list[COREntry],
        *,
        normalized_surface: str,
        preferred_pos_tag: str | None,
    ) -> COREntry | None:
        if not entries:
            return None
        filtered = entries
        if preferred_pos_tag:
            preferred = [e for e in entries if e.pos_tag == preferred_pos_tag]
            if preferred:
                filtered = preferred
        return min(filtered, key=lambda e: _cor_entry_priority(e, normalized_surface))

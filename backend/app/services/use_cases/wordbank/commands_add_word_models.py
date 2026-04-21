from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AddWordCommandInputs:
    normalized_surface: str
    stored_lemma: str
    normalized_cor_id: str | None
    selected_pos_tag: str | None
    selected_morphology: str | None


@dataclass(frozen=True, slots=True)
class WordMetadata:
    translation: str | None
    provider: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass(frozen=True, slots=True)
class AddWordWriteResult:
    inserted_lexeme: bool
    inserted_meaning: bool
    inserted_surface_form: bool
    inserted_lemma_surface_form: bool
    inserted_cor_variant: bool

    @property
    def inserted_any(self) -> bool:
        return (
            self.inserted_lexeme
            or self.inserted_meaning
            or self.inserted_surface_form
            or self.inserted_lemma_surface_form
            or self.inserted_cor_variant
        )

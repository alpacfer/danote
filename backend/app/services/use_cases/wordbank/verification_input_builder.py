from __future__ import annotations

from typing import Literal

from app.db.migrations import get_connection
from app.db.repositories.wordbank import WordbankRepository
from app.services.use_cases.wordbank.collaborators.cor import CorResolutionCollaborator
from app.services.use_cases.wordbank.gloss_translations import is_likely_english_gloss
from app.services.use_cases.wordbank.collaborators.nlp import NLPCollaborator
from app.services.use_cases.wordbank.verification_categories import (
    persisted_category_labels_for_scope,
)
from app.services.verification import (
    WordVerificationInput,
    WordVerificationMeaningSection,
    WordVerificationSurfaceForm,
)


def build_verification_input(
    *,
    db_path,
    nlp: NLPCollaborator,
    cor: CorResolutionCollaborator,
    owner_user_id: int = 1,
    stored_lemma: str,
    stored_surface_form: str | None,
    meaning_id: int | None,
    review_intent: Literal["general", "complete_variations"] = "general",
) -> WordVerificationInput:
    lexeme_source = "manual"
    selected_translation: str | None = None
    selected_translation_scope: Literal["lemma", "meaning_section"] | None = None
    surface_source: str | None = None
    meaning_key: str | None = None
    meaning_gloss: str | None = None
    meaning_gloss_translation: str | None = None
    sibling_meaning_sections: list[WordVerificationMeaningSection] = []
    lexeme_pos_tag: str | None = None
    lexeme_morphology: str | None = None
    selected_meaning_pos_tag: str | None = None
    selected_meaning_morphology: str | None = None
    selected_surface_pos_tag: str | None = None
    selected_surface_morphology: str | None = None
    selected_surface_row = None
    surface_cor_entry = None
    canonical_lemma_entry = None
    meaning_rows_by_id: dict[int, object] = {}
    meaning_gloss_translations_by_id: dict[int, str | None] = {}
    surface_rows = []

    with get_connection(db_path) as conn:
        lexeme_row = conn.execute(
            """
            SELECT id, source, english_translation, pos_tag, morphology
            FROM lexemes
            WHERE owner_user_id = ? AND lemma = ?
            LIMIT 1
            """,
            (owner_user_id, stored_lemma),
        ).fetchone()

        if lexeme_row is not None:
            lexeme_source = lexeme_row["source"]
            lexeme_pos_tag = lexeme_row["pos_tag"]
            lexeme_morphology = lexeme_row["morphology"]
            meaning_rows = conn.execute(
                """
                SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
                FROM lexeme_meanings
                WHERE lexeme_id = ?
                ORDER BY id ASC
                """,
                (int(lexeme_row["id"]),),
            ).fetchall()
            surface_rows = conn.execute(
                """
                SELECT
                    sf.form,
                    sf.meaning_id,
                    sf.source,
                    sf.pos_tag,
                    sf.morphology,
                    (
                        SELECT sfcv.cor_id
                        FROM surface_form_cor_variants sfcv
                        WHERE sfcv.surface_form_id = sf.id
                        ORDER BY sfcv.id ASC
                        LIMIT 1
                    ) AS cor_id
                FROM surface_forms sf
                WHERE sf.lexeme_id = ?
                ORDER BY sf.id ASC
                """,
                (int(lexeme_row["id"]),),
            ).fetchall()
            meaning_rows_by_id = {
                int(row["id"]): row
                for row in meaning_rows
            }
            forms_by_meaning: dict[int, list[str]] = {}
            for row in surface_rows:
                if row["meaning_id"] is None:
                    continue
                forms_by_meaning.setdefault(int(row["meaning_id"]), []).append(str(row["form"]))
            gloss_translation_cache: dict[
                tuple[str, str, str | None, str | None, str, str | None, str | None],
                str | None,
            ] = {}
            meaning_gloss_translations_by_id = {
                int(row["id"]): _meaning_gloss_translation(
                    cor=cor,
                    lexeme_lemma=stored_lemma,
                    lexeme_pos_tag=lexeme_pos_tag,
                    meaning_gloss=row["gloss"],
                    meaning_translation=row["english_translation"],
                    meaning_pos_tag=row["pos_tag"],
                    cor_lemma_idx=(
                        int(row["cor_lemma_idx"])
                        if row["cor_lemma_idx"] is not None
                        else None
                    ),
                    cache=gloss_translation_cache,
                )
                for row in meaning_rows
            }

            meaning_row = _load_meaning_row(
                conn,
                lexeme_id=int(lexeme_row["id"]),
                requested_meaning_id=meaning_id,
                normalized_lemma=stored_lemma,
            )
            if meaning_row is not None:
                selected_translation = meaning_row["english_translation"]
                selected_translation_scope = "meaning_section" if selected_translation else None
                meaning_key = meaning_row["meaning_key"]
                meaning_gloss = meaning_row["gloss"]
                meaning_gloss_translation = meaning_gloss_translations_by_id.get(int(meaning_row["id"]))
                selected_meaning_pos_tag = meaning_row["pos_tag"]
                selected_meaning_morphology = meaning_row["morphology"]
            else:
                selected_translation = lexeme_row["english_translation"]
                selected_translation_scope = "lemma" if selected_translation else None

            sibling_meaning_sections = [
                WordVerificationMeaningSection(
                    id=int(row["id"]),
                    meaning_key=str(row["meaning_key"]),
                    gloss=row["gloss"],
                    gloss_translation=meaning_gloss_translations_by_id.get(int(row["id"])),
                    english_translation=row["english_translation"],
                    pos_tag=row["pos_tag"],
                    morphology=row["morphology"],
                    surface_forms=tuple(forms_by_meaning.get(int(row["id"]), [])),
                )
                for row in meaning_rows
                if meaning_id is None or int(row["id"]) != meaning_id
            ]

            if stored_surface_form:
                selected_surface_row = _select_surface_row(
                    surface_rows,
                    stored_surface_form=stored_surface_form,
                    meaning_id=meaning_id,
                )
                if selected_surface_row is not None:
                    surface_source = selected_surface_row["source"]
                    selected_surface_pos_tag = selected_surface_row["pos_tag"]
                    selected_surface_morphology = selected_surface_row["morphology"]
                    surface_cor_entry = cor.cor_local_entry_for_cor_id(
                        cor_id=selected_surface_row["cor_id"]
                    ) if selected_surface_row["cor_id"] else None

            canonical_lemma_entry = _resolve_canonical_lemma_entry(
                cor=cor,
                stored_lemma=stored_lemma,
                meaning_row=meaning_row,
                selected_surface_row=selected_surface_row,
                fallback_pos_tag=selected_meaning_pos_tag or lexeme_pos_tag,
            )
            if stored_surface_form and surface_cor_entry is None:
                surface_cor_entry = cor.best_cor_local_entry_for_form(
                    form=stored_surface_form,
                    lemma=stored_lemma,
                    preferred_pos_tag=selected_surface_pos_tag or selected_meaning_pos_tag or lexeme_pos_tag,
                )

    repository = WordbankRepository(db_path, owner_user_id=owner_user_id)
    current_categories: tuple[str, ...] = ()
    available_categories: tuple[str, ...] = ()
    available_surface_forms: tuple[WordVerificationSurfaceForm, ...] = ()
    lexeme = repository.get_lexeme(stored_lemma)
    if lexeme is not None:
        current_categories = tuple(
            persisted_category_labels_for_scope(
                repository,
                lexeme_id=lexeme.id,
                meaning_id=meaning_id,
            )
        )
        available_categories = tuple(
            category.label for category in repository.list_word_categories()
        )
        available_surface_forms = tuple(
            WordVerificationSurfaceForm(
                form=str(row["form"]),
                meaning_id=int(row["meaning_id"]) if row["meaning_id"] is not None else None,
                meaning_key=(
                    str(meaning_rows_by_id[int(row["meaning_id"])]["meaning_key"])
                    if row["meaning_id"] is not None and int(row["meaning_id"]) in meaning_rows_by_id
                    else None
                ),
                gloss=(
                    meaning_rows_by_id[int(row["meaning_id"])]["gloss"]
                    if row["meaning_id"] is not None and int(row["meaning_id"]) in meaning_rows_by_id
                    else None
                ),
                gloss_translation=(
                    meaning_gloss_translations_by_id.get(int(row["meaning_id"]))
                    if row["meaning_id"] is not None
                    else None
                ),
                english_translation=(
                    meaning_rows_by_id[int(row["meaning_id"])]["english_translation"]
                    if row["meaning_id"] is not None and int(row["meaning_id"]) in meaning_rows_by_id
                    else lexeme_row["english_translation"] if lexeme_row is not None else None
                ),
                pos_tag=row["pos_tag"],
                morphology=row["morphology"],
                source=row["source"],
                gram_raw=_surface_form_gram_raw(
                    cor=cor,
                    stored_lemma=stored_lemma,
                    form_row=row,
                    meaning_row=(
                        meaning_rows_by_id.get(int(row["meaning_id"]))
                        if row["meaning_id"] is not None
                        else None
                    ),
                ),
            )
            for row in surface_rows if lexeme_row is not None
        )

    canonical_lemma_pos_tag, canonical_lemma_morphology = _resolve_canonical_lemma_metadata(
        nlp=nlp,
        stored_lemma=stored_lemma,
        lexeme_pos_tag=lexeme_pos_tag,
        lexeme_morphology=lexeme_morphology,
        selected_meaning_pos_tag=selected_meaning_pos_tag,
        selected_meaning_morphology=selected_meaning_morphology,
        canonical_lemma_entry=canonical_lemma_entry,
    )
    if selected_meaning_pos_tag is None:
        selected_meaning_pos_tag = canonical_lemma_entry.pos_tag if canonical_lemma_entry is not None else None
    if selected_meaning_morphology is None:
        selected_meaning_morphology = (
            canonical_lemma_entry.morphology if canonical_lemma_entry is not None else None
        )
    if stored_surface_form and selected_surface_pos_tag is None:
        selected_surface_pos_tag = surface_cor_entry.pos_tag if surface_cor_entry is not None else None
    if stored_surface_form and selected_surface_morphology is None:
        selected_surface_morphology = surface_cor_entry.morphology if surface_cor_entry is not None else None
    if canonical_lemma_pos_tag is None or canonical_lemma_morphology is None:
        inferred_lemma_pos_tag, inferred_lemma_morphology = nlp.extract_pos_and_morphology(stored_lemma)
        canonical_lemma_pos_tag = canonical_lemma_pos_tag or inferred_lemma_pos_tag
        canonical_lemma_morphology = canonical_lemma_morphology or inferred_lemma_morphology
    if stored_surface_form and (selected_surface_pos_tag is None or selected_surface_morphology is None):
        inferred_surface_pos_tag, inferred_surface_morphology = nlp.extract_pos_and_morphology(
            stored_surface_form
        )
        selected_surface_pos_tag = selected_surface_pos_tag or inferred_surface_pos_tag
        selected_surface_morphology = selected_surface_morphology or inferred_surface_morphology

    return WordVerificationInput(
        stored_lemma=stored_lemma,
        stored_surface_form=stored_surface_form,
        meaning_id=meaning_id,
        meaning_key=meaning_key,
        meaning_gloss=meaning_gloss,
        meaning_gloss_translation=meaning_gloss_translation,
        lexeme_source=lexeme_source,
        selected_translation=selected_translation,
        selected_translation_scope=selected_translation_scope,
        surface_source=surface_source,
        canonical_lemma=(
            canonical_lemma_entry.lemma if canonical_lemma_entry is not None else stored_lemma
        ),
        canonical_lemma_pos_tag=canonical_lemma_pos_tag,
        canonical_lemma_morphology=canonical_lemma_morphology,
        selected_meaning_pos_tag=selected_meaning_pos_tag,
        selected_meaning_morphology=selected_meaning_morphology,
        selected_surface_pos_tag=selected_surface_pos_tag,
        selected_surface_morphology=selected_surface_morphology,
        current_categories=current_categories,
        available_categories=available_categories,
        sibling_meaning_sections=tuple(sibling_meaning_sections),
        available_surface_forms=available_surface_forms,
        review_intent=review_intent,
    )


def _meaning_gloss_translation(
    *,
    cor: CorResolutionCollaborator,
    lexeme_lemma: str,
    lexeme_pos_tag: str | None,
    meaning_gloss: str | None,
    meaning_translation: str | None,
    meaning_pos_tag: str | None,
    cor_lemma_idx: int | None,
    cache: dict[tuple[str, str, str | None, str | None, str, str | None, str | None], str | None],
) -> str | None:
    normalized_meaning_gloss = " ".join((meaning_gloss or "").strip().split()).lower()
    normalized_meaning_translation = " ".join((meaning_translation or "").strip().split()).lower()
    if normalized_meaning_gloss and normalized_meaning_gloss == normalized_meaning_translation:
        return meaning_gloss
    if cor_lemma_idx is None:
        return meaning_gloss if is_likely_english_gloss(meaning_gloss) else None
    cor_entry = cor.best_cor_local_lemma_entry(
        lemma_idx=cor_lemma_idx,
        lemma=lexeme_lemma,
        preferred_pos_tag=meaning_pos_tag or lexeme_pos_tag,
    )
    if cor_entry is None:
        return meaning_gloss if is_likely_english_gloss(meaning_gloss) else None
    translated = cor.lookup_translation_for_cor_gloss(
        entry=cor_entry,
        lemma_translation=meaning_translation,
        cache=cache,
    )
    normalized_translated = " ".join((translated or "").strip().split()).lower()
    if normalized_translated and normalized_translated != normalized_meaning_gloss:
        return translated
    if normalized_translated and is_likely_english_gloss(meaning_gloss):
        return translated
    return meaning_gloss if is_likely_english_gloss(meaning_gloss) else None


def _select_surface_row(surface_rows, *, stored_surface_form: str, meaning_id: int | None):
    for row in surface_rows:
        if str(row["form"]) != stored_surface_form:
            continue
        row_meaning_id = int(row["meaning_id"]) if row["meaning_id"] is not None else None
        if row_meaning_id == meaning_id:
            return row
    return None


def _surface_form_gram_raw(
    *,
    cor: CorResolutionCollaborator,
    stored_lemma: str,
    form_row,
    meaning_row,
) -> str | None:
    preferred_pos_tag = (
        meaning_row["pos_tag"]
        if meaning_row is not None and meaning_row["pos_tag"] is not None
        else form_row["pos_tag"]
    )
    preferred_lemma_idx = (
        int(meaning_row["cor_lemma_idx"])
        if meaning_row is not None and meaning_row["cor_lemma_idx"] is not None
        else None
    )
    cor_entry = cor.best_cor_local_entry_for_form(
        form=str(form_row["form"]),
        lemma=stored_lemma,
        preferred_pos_tag=preferred_pos_tag,
        preferred_lemma_idx=preferred_lemma_idx,
    )
    if cor_entry is not None:
        return cor_entry.gram_raw
    if form_row["cor_id"]:
        fallback_entry = cor.cor_local_entry_for_cor_id(cor_id=str(form_row["cor_id"]))
        if fallback_entry is not None:
            return fallback_entry.gram_raw
    return None


def _resolve_canonical_lemma_entry(
    *,
    cor: CorResolutionCollaborator,
    stored_lemma: str,
    meaning_row,
    selected_surface_row,
    fallback_pos_tag: str | None,
):
    cor_lemma_idx = int(meaning_row["cor_lemma_idx"]) if meaning_row is not None and meaning_row["cor_lemma_idx"] is not None else None
    if cor_lemma_idx is not None:
        entry = cor.best_cor_local_lemma_entry(
            lemma_idx=cor_lemma_idx,
            lemma=stored_lemma,
            preferred_pos_tag=fallback_pos_tag,
            allow_lemma_mismatch=True,
        )
        if entry is not None:
            return entry
    if selected_surface_row is None or not selected_surface_row["cor_id"]:
        return None
    surface_entry = cor.cor_local_entry_for_cor_id(cor_id=str(selected_surface_row["cor_id"]))
    if surface_entry is None:
        return None
    return cor.best_cor_local_lemma_entry(
        lemma_idx=surface_entry.lemma_idx,
        lemma=stored_lemma,
        preferred_pos_tag=fallback_pos_tag or surface_entry.pos_tag,
        allow_lemma_mismatch=True,
    )


def _resolve_canonical_lemma_metadata(
    *,
    nlp: NLPCollaborator,
    stored_lemma: str,
    lexeme_pos_tag: str | None,
    lexeme_morphology: str | None,
    selected_meaning_pos_tag: str | None,
    selected_meaning_morphology: str | None,
    canonical_lemma_entry,
) -> tuple[str | None, str | None]:
    canonical_pos_tag = (
        canonical_lemma_entry.pos_tag if canonical_lemma_entry is not None else None
    ) or lexeme_pos_tag or selected_meaning_pos_tag
    canonical_morphology = (
        canonical_lemma_entry.morphology if canonical_lemma_entry is not None else None
    ) or lexeme_morphology or selected_meaning_morphology
    if canonical_pos_tag is not None and canonical_morphology is not None:
        return canonical_pos_tag, canonical_morphology
    inferred_pos_tag, inferred_morphology = nlp.extract_pos_and_morphology(stored_lemma)
    return canonical_pos_tag or inferred_pos_tag, canonical_morphology or inferred_morphology


def _load_meaning_row(
    conn,
    *,
    lexeme_id: int,
    requested_meaning_id: int | None,
    normalized_lemma: str,
):
    if requested_meaning_id is not None:
        meaning_row = conn.execute(
            """
            SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
            FROM lexeme_meanings
            WHERE id = ? AND lexeme_id = ?
            LIMIT 1
            """,
            (requested_meaning_id, lexeme_id),
        ).fetchone()
        if meaning_row is None:
            raise LookupError(f"Meaning '{requested_meaning_id}' was not found for '{normalized_lemma}'")
        return meaning_row

    meaning_rows = conn.execute(
        """
        SELECT id, meaning_key, cor_lemma_idx, gloss, english_translation, pos_tag, morphology
        FROM lexeme_meanings
        WHERE lexeme_id = ?
        ORDER BY id ASC
        LIMIT 2
        """,
        (lexeme_id,),
    ).fetchall()
    if len(meaning_rows) == 1:
        return meaning_rows[0]
    return None

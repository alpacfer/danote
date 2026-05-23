from __future__ import annotations

import re

from app.api.schemas.v1.wordbank import LemmaDetailsResponse
from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.shared import _normalize_action_value


def normalize_comparable(value: str) -> str:
    return " ".join(value.strip().lower().split())


def cor_translation_frame(entry: CORLocalEntry) -> tuple[str, str]:
    lemma = normalize_token(entry.lemma)
    if not lemma:
        return "raw", entry.lemma

    gram = entry.gram_raw.lower()
    pos_code = gram.split(".", 1)[0].strip()
    if pos_code == "vb":
        return "verb", f"at {lemma}"
    if pos_code == "sb":
        article = "et" if re.search(r"(^|\.)itk(\.|$)", gram) else "en"
        return "noun", f"{article} {lemma}"
    if pos_code == "adj":
        return "adjective", f"en {lemma} ting"
    if pos_code == "adv":
        return "adverb", f"han gør det {lemma}"
    if pos_code == "pron":
        return "pronoun", f"{lemma} er her"
    if pos_code == "præp":
        return "preposition", f"{lemma} huset"
    if pos_code == "konj":
        return "conjunction", f"..., {lemma} jeg går"
    if pos_code == "art":
        return "article", f"{lemma} bog"
    if pos_code == "prop":
        return "proper_noun", f"navnet {lemma}"
    if pos_code == "talord":
        return "numeral", f"{lemma} bøger"
    return "raw", lemma


def strip_cor_translation_frame(frame_kind: str, translated: str) -> str | None:
    cleaned = normalize_token(translated)
    if not cleaned:
        return None
    if frame_kind == "verb":
        return cleaned

    value = cleaned
    if frame_kind == "noun":
        value = re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "adjective":
        value = re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE)
        value = re.sub(r"\s+things?$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "adverb":
        value = re.sub(r"^(?:he|she|it)\s+does\s+it\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "pronoun":
        value = re.sub(r"\s+is\s+here$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "preposition":
        value = re.sub(r"\s+(?:the\s+)?house$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "conjunction":
        value = re.sub(r"\s+i\s+go$", "", value, flags=re.IGNORECASE)
        value = value.strip(" ,")
    elif frame_kind == "article":
        value = re.sub(r"\s+books?$", "", value, flags=re.IGNORECASE)
    elif frame_kind == "proper_noun":
        value = re.sub(r"^(?:the\s+)?name\s+", "", value, flags=re.IGNORECASE)
    elif frame_kind == "numeral":
        value = re.sub(r"\s+books?$", "", value, flags=re.IGNORECASE)

    value = normalize_token(value)
    return value or cleaned


def cor_entry_priority(entry: COREntry, normalized_surface: str) -> tuple[int, int, int, int, str, str]:
    norm_value = (entry.norm or "").strip().lower()
    if norm_value == "norm":
        norm_rank = 0
    elif norm_value == "accept":
        norm_rank = 1
    elif norm_value == "add":
        norm_rank = 2
    else:
        norm_rank = 3
    is_exact_surface = 0 if _normalize_action_value(entry.full_form) == _normalize_action_value(normalized_surface) else 1
    lemma_matches_surface = 0 if _normalize_action_value(entry.lemma) == _normalize_action_value(normalized_surface) else 1
    noun_number_rank = 2
    if entry.pos_tag == "NOUN":
        if entry.morphology and "Number=Sing" in entry.morphology:
            noun_number_rank = 0
        elif entry.morphology and "Number=Plur" in entry.morphology:
            noun_number_rank = 1
    return (
        is_exact_surface,
        lemma_matches_surface,
        noun_number_rank,
        norm_rank,
        entry.lemma,
        entry.pos_tag or "",
    )


def normalize_translation_value(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = " ".join(value.strip().split())
    if not cleaned:
        return None
    return cleaned.lower()


def map_lemma_details_response(response: LemmaDetailsResponse) -> LemmaDetailsResponse:
    if response.is_sectioned:
        return response

    non_lemma_form_count = sum(1 for form in response.surface_forms if form.form != response.lemma)
    surface_forms: list[LemmaDetailsResponse.SurfaceFormDetails] = []
    for form in response.surface_forms:
        if (
            form.form == response.lemma
            and non_lemma_form_count <= 1
            and not form.has_pronunciation
        ):
            continue
        surface_forms.append(
            LemmaDetailsResponse.SurfaceFormDetails(
                form=form.form,
                pos_tag=form.pos_tag,
                morphology=form.morphology,
                lemma=None,
                lemma_translation=(
                    None if form.lemma_translation == response.english_translation else form.lemma_translation
                ),
                gloss=form.gloss,
                gloss_translation=form.gloss_translation,
                gram_raw=form.gram_raw,
                has_pronunciation=form.has_pronunciation,
                verification=form.verification,
            )
        )

    return LemmaDetailsResponse(
        lemma=response.lemma,
        english_translation=response.english_translation,
        additional_translations=response.additional_translations,
        pos_tag=response.pos_tag,
        morphology=response.morphology,
        is_sectioned=False,
        categories=response.categories,
        verification=response.verification,
        meaning_sections=[],
        surface_forms=surface_forms,
        related_words=response.related_words,
        linked_sentences=response.linked_sentences,
    )

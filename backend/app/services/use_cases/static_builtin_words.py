from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.token_classifier import normalize_token
from app.services.use_cases.static_hv_words import static_hv_word_for_token
from app.services.use_cases.static_presaved_words import (
    StaticPresavedWord,
    static_presaved_words_for_token,
)
from app.services.use_cases.static_pronouns import static_pronoun_for_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime


@dataclass(frozen=True, slots=True)
class StaticReferenceLink:
    page_id: Literal["pronouns", "function_words", "numbers_time"]
    page_title: str
    tab_id: str
    tab_title: str
    sentinel: str


@dataclass(frozen=True, slots=True)
class StaticBuiltinSense:
    lemma: str
    meaning_key: str
    english_translation: str
    pos_tag: str | None
    morphology: str | None
    provider: str
    reference_links: tuple[StaticReferenceLink, ...] = ()


def static_builtin_senses_for_token(token: str | None) -> tuple[StaticBuiltinSense, ...]:
    normalized = normalize_token(token or "")
    if not normalized:
        return ()

    senses: list[StaticBuiltinSense] = []
    for word in static_presaved_words_for_token(normalized):
        senses.append(_sense_from_presaved_word(word))

    hv_word = static_hv_word_for_token(normalized)
    if hv_word is not None:
        senses.append(
            StaticBuiltinSense(
                lemma=hv_word.lemma,
                meaning_key="question_word",
                english_translation=hv_word.english_translation,
                pos_tag=hv_word.pos_tag,
                morphology=hv_word.morphology,
                provider="static_hv_word",
                reference_links=(_reference_link("pronouns", "question_words"),),
            )
        )

    if normalized != "i":
        skip_interrogative_pronoun = hv_word is not None
        for pronoun_sense in _pronoun_senses(normalized):
            if skip_interrogative_pronoun and pronoun_sense.meaning_key in {
                "interrogative_pronoun",
                "relative_pronoun",
            }:
                continue
            senses.append(pronoun_sense)

    deduped: list[StaticBuiltinSense] = []
    seen: set[tuple[str, str, str]] = set()
    for sense in senses:
        translation_key = _canonical_translation_key(sense.english_translation)
        pos_key = (sense.pos_tag or "").upper()
        key = (sense.lemma, pos_key, translation_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(sense)
    return tuple(deduped)


def select_static_builtin_sense(
    token: str | None,
    *,
    pos_tag: str | None,
    morphology: str | None = None,
    english_translation: str | None = None,
) -> StaticBuiltinSense | None:
    senses = static_builtin_senses_for_token(token)
    if not senses:
        return None
    normalized_translation = normalize_token(english_translation or "")
    if normalized_translation:
        translated = next(
            (
                sense
                for sense in senses
                if normalized_translation in _normalized_translation_parts(sense.english_translation)
            ),
            None,
        )
        if translated is not None:
            return translated
    normalized_morphology = morphology or ""
    if normalized_morphology:
        matched_morphology = _select_by_morphology(senses, normalized_morphology)
        if matched_morphology is not None:
            return matched_morphology
    normalized_pos = (pos_tag or "").upper()
    if normalized_pos:
        matched_pos = next((sense for sense in senses if (sense.pos_tag or "").upper() == normalized_pos), None)
        if matched_pos is not None:
            return matched_pos
    return senses[0]


def ensure_static_builtin_sense(
    runtime: WordbankRuntime,
    sense: StaticBuiltinSense,
) -> tuple[int, int | None]:
    senses = static_builtin_senses_for_token(sense.lemma)
    should_section = len(senses) > 1
    lexeme_id, _inserted_lexeme = runtime.repository.insert_or_load_lexeme(
        stored_lemma=sense.lemma,
        translation=None if should_section else sense.english_translation,
        provider=None if should_section else sense.provider,
        pos_tag=None if should_section else sense.pos_tag,
        morphology=None if should_section else sense.morphology,
        source="static",
    )
    if not should_section:
        runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=None,
            form=sense.lemma,
            pos_tag=sense.pos_tag,
            morphology=sense.morphology,
            source="static",
        )
        return lexeme_id, None

    selected_meaning_id: int | None = None
    for static_sense in senses:
        meaning, _inserted_meaning = runtime.repository.upsert_lexeme_meaning(
            lexeme_id=lexeme_id,
            meaning_key=static_sense.meaning_key,
            cor_lemma_idx=None,
            dictionary_status="unknown",
            gloss=None,
            english_translation=static_sense.english_translation,
            pos_tag=static_sense.pos_tag,
            morphology=static_sense.morphology,
        )
        runtime.repository.insert_or_update_surface_form(
            lexeme_id=lexeme_id,
            meaning_id=meaning.id,
            form=static_sense.lemma,
            pos_tag=static_sense.pos_tag,
            morphology=static_sense.morphology,
            source="static",
        )
        if static_sense.meaning_key == sense.meaning_key and static_sense.pos_tag == sense.pos_tag:
            selected_meaning_id = meaning.id
    return lexeme_id, selected_meaning_id


def static_builtin_reference_links(
    lemma: str | None,
    *,
    meaning_key: str | None,
    pos_tag: str | None,
) -> tuple[StaticReferenceLink, ...]:
    senses = static_builtin_senses_for_token(lemma)
    if not senses:
        return ()
    normalized_meaning_key = meaning_key or ""
    normalized_pos = (pos_tag or "").upper()
    for sense in senses:
        if sense.meaning_key == normalized_meaning_key and (sense.pos_tag or "").upper() == normalized_pos:
            return sense.reference_links
    for sense in senses:
        if sense.meaning_key == normalized_meaning_key:
            return sense.reference_links
    if normalized_pos:
        for sense in senses:
            if (sense.pos_tag or "").upper() == normalized_pos:
                return sense.reference_links
    return ()


def _sense_from_presaved_word(word: StaticPresavedWord) -> StaticBuiltinSense:
    meaning_key = word.meaning_key or normalize_token(word.english_translation) or word.lemma
    return StaticBuiltinSense(
        lemma=word.lemma,
        meaning_key=meaning_key,
        english_translation=word.english_translation,
        pos_tag=word.pos_tag,
        morphology=word.morphology,
        provider="static_presaved_word",
        reference_links=_reference_links_for_presaved(word, meaning_key=meaning_key),
    )


def _pronoun_meaning_key(morphology: str | None) -> str:
    normalized = morphology or ""
    if "PronType=Rel" in normalized:
        return "relative_pronoun"
    if "PronType=Int" in normalized:
        return "interrogative_pronoun"
    if "PronType=Dem" in normalized or "PronType=Prs,Dem" in normalized:
        return "demonstrative_pronoun"
    if "Poss=Yes" in normalized:
        return "possessive_pronoun"
    return "pronoun"


def _pronoun_senses(normalized: str) -> tuple[StaticBuiltinSense, ...]:
    pronoun = static_pronoun_for_token(normalized)
    if pronoun is None:
        return ()
    if normalized in {"den", "det", "de"}:
        personal_translation = {"den": "it", "det": "it", "de": "they"}[normalized]
        demonstrative_translation = {"den": "that", "det": "that", "de": "those"}[normalized]
        personal_morphology = {
            "den": "PronType=Prs|Person=3|Number=Sing|Gender=Com",
            "det": "PronType=Prs|Person=3|Number=Sing|Gender=Neut",
            "de": "PronType=Prs|Case=Nom|Person=3|Number=Plur",
        }[normalized]
        demonstrative_morphology = {
            "den": "PronType=Dem|Number=Sing|Gender=Com",
            "det": "PronType=Dem|Number=Sing|Gender=Neut",
            "de": "PronType=Dem|Number=Plur",
        }[normalized]
        return (
            StaticBuiltinSense(
                lemma=pronoun.lemma,
                meaning_key="personal_pronoun",
                english_translation=personal_translation,
                pos_tag=pronoun.pos_tag,
                morphology=personal_morphology,
                provider="static_pronoun",
                reference_links=(_reference_link("pronouns", "personal"),),
            ),
            StaticBuiltinSense(
                lemma=pronoun.lemma,
                meaning_key="demonstrative_pronoun",
                english_translation=demonstrative_translation,
                pos_tag=pronoun.pos_tag,
                morphology=demonstrative_morphology,
                provider="static_pronoun",
                reference_links=(_reference_link("pronouns", "demonstrative"),),
            ),
        )
    key = _pronoun_meaning_key(pronoun.morphology)
    return (
        StaticBuiltinSense(
            lemma=pronoun.lemma,
            meaning_key=key,
            english_translation=pronoun.english_translation,
            pos_tag=pronoun.pos_tag,
            morphology=pronoun.morphology,
            provider="static_pronoun",
            reference_links=(_reference_link("pronouns", _pronoun_tab_for_key(key)),),
        ),
    )


def _pronoun_tab_for_key(meaning_key: str) -> str:
    if meaning_key == "relative_pronoun":
        return "relative"
    if meaning_key == "interrogative_pronoun":
        return "question_words"
    if meaning_key == "demonstrative_pronoun":
        return "demonstrative"
    if meaning_key == "possessive_pronoun":
        return "possessive"
    if meaning_key in {"indefinite_pronoun", "negative_pronoun", "total_pronoun", "reciprocal_pronoun"}:
        return "indefinite"
    return "personal"


def _reference_links_for_presaved(
    word: StaticPresavedWord,
    *,
    meaning_key: str,
) -> tuple[StaticReferenceLink, ...]:
    pos = (word.pos_tag or "").upper()
    if meaning_key == "article" or pos == "DET":
        return (_reference_link("function_words", "articles"),)
    if meaning_key == "number" or pos == "NUM":
        return (_reference_link("numbers_time", "cardinal_numbers"),)
    if pos == "ADP":
        return (_reference_link("function_words", "prepositions"),)
    if pos in {"CCONJ", "SCONJ"}:
        return (_reference_link("function_words", "conjunctions"),)
    if pos == "ADJ" and meaning_key in {"ordinal", "first", "second", "third"}:
        return (_reference_link("numbers_time", "ordinal_numbers"),)
    return ()


_PAGE_LABELS = {
    "pronouns": "Pronouns",
    "function_words": "Function Words",
    "numbers_time": "Numbers & Time",
}

_TAB_LABELS = {
    "personal": "Personal",
    "possessive": "Possessive",
    "demonstrative": "Demonstrative",
    "relative": "Relative",
    "indefinite": "Indefinite",
    "question_words": "Question Words",
    "articles": "Articles",
    "prepositions": "Prepositions",
    "conjunctions": "Conjunctions",
    "cardinal_numbers": "Cardinal Numbers",
    "ordinal_numbers": "Ordinal Numbers",
}

_TAB_SENTINELS = {
    ("pronouns", "personal"): "__pinned_pronouns_personal",
    ("pronouns", "possessive"): "__pinned_pronouns_possessive",
    ("pronouns", "demonstrative"): "__pinned_pronouns_demonstrative",
    ("pronouns", "relative"): "__pinned_pronouns_relative",
    ("pronouns", "indefinite"): "__pinned_pronouns_indefinite",
    ("pronouns", "question_words"): "__pinned_pronouns_question_words",
    ("function_words", "articles"): "__pinned_function_words_articles",
    ("function_words", "prepositions"): "__pinned_function_words_prepositions",
    ("function_words", "conjunctions"): "__pinned_function_words_conjunctions",
    ("numbers_time", "cardinal_numbers"): "__pinned_numbers_time_cardinal_numbers",
    ("numbers_time", "ordinal_numbers"): "__pinned_numbers_time_ordinal_numbers",
}


def _reference_link(page_id: str, tab_id: str) -> StaticReferenceLink:
    return StaticReferenceLink(
        page_id=page_id,  # type: ignore[arg-type]
        page_title=_PAGE_LABELS[page_id],
        tab_id=tab_id,
        tab_title=_TAB_LABELS[tab_id],
        sentinel=_TAB_SENTINELS[(page_id, tab_id)],
    )


def _canonical_translation_key(translation: str) -> str:
    return " ".join(translation.replace("/", " ").split()).casefold()


def _normalized_translation_parts(translation: str) -> set[str]:
    normalized = normalize_token(translation)
    parts = {
        normalize_token(part)
        for part in translation.replace("(", "/").replace(")", "").split("/")
    }
    parts.add(normalized)
    parts.discard("")
    return parts


def _select_by_morphology(
    senses: tuple[StaticBuiltinSense, ...],
    morphology: str,
) -> StaticBuiltinSense | None:
    if "PronType=Dem" in morphology:
        return next((sense for sense in senses if sense.meaning_key == "demonstrative_pronoun"), None)
    if "PronType=Prs" in morphology:
        return next((sense for sense in senses if sense.meaning_key == "personal_pronoun"), None)
    if "PronType=Rel" in morphology:
        return next((sense for sense in senses if sense.meaning_key == "relative_pronoun"), None)
    if "PronType=Int" in morphology:
        return next((sense for sense in senses if sense.meaning_key == "interrogative_pronoun"), None)
    return None

from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token

_ARTICLE_TOKENS = {"a", "an", "the"}
_LEADING_FUNCTION_TOKENS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "that",
    "the",
    "to",
    "with",
}
_GENERIC_SUFFIX_NOUNS = {
    "clause",
    "clauses",
    "house",
    "houses",
    "item",
    "items",
    "man",
    "men",
    "name",
    "names",
    "object",
    "objects",
    "one",
    "ones",
    "person",
    "people",
    "thing",
    "things",
    "time",
    "times",
    "woman",
    "women",
}
_COUNTED_SUFFIX_NOUNS = {
    "book",
    "books",
    "item",
    "items",
    "thing",
    "things",
    "time",
    "times",
}
_SHORT_GENERIC_OBJECTS = {
    "he",
    "her",
    "him",
    "house",
    "it",
    "me",
    "someone",
    "something",
    "the",
    "them",
    "this",
    "us",
    "you",
}
_LEXICALIZED_PREPOSITIONS = {
    "according to",
    "apart from",
    "because of",
    "due to",
    "except for",
    "in front of",
    "instead of",
    "next to",
    "out of",
    "up to",
}
_LEXICALIZED_CONJUNCTIONS = {
    "as if",
    "as long as",
    "as soon as",
    "even if",
    "even though",
    "in case",
    "provided that",
    "rather than",
    "so that",
}
_LEXICALIZED_PRONOUNS = {
    "each other",
    "one another",
}
_ALLOWED_CHARS_RE = re.compile(r"^[a-z][a-z' -]*$")


@dataclass(frozen=True, slots=True)
class WordTranslationFrame:
    kind: str
    text: str


def cor_local_word_translation_frame(entry: CORLocalEntry) -> WordTranslationFrame:
    return build_word_translation_frame(
        lemma=entry.lemma,
        pos_tag=entry.pos_tag,
        pos_code=_gram_pos_code(entry.gram_raw),
        gram_or_function=entry.gram_raw,
        morphology=entry.morphology,
    )


def cor_entry_word_translation_frame(entry: COREntry) -> WordTranslationFrame:
    grammatical_function = entry.grammatical_function or ""
    pos_code = (entry.ordklasse or "").strip().lower() or _gram_pos_code(grammatical_function)
    return build_word_translation_frame(
        lemma=entry.lemma,
        pos_tag=entry.pos_tag,
        pos_code=pos_code,
        gram_or_function=grammatical_function,
        morphology=entry.morphology,
    )


def build_word_translation_frame(
    *,
    lemma: str,
    pos_tag: str | None = None,
    pos_code: str | None = None,
    gram_or_function: str | None = None,
    morphology: str | None = None,
) -> WordTranslationFrame:
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        return WordTranslationFrame(kind="raw", text=lemma)

    normalized_pos = (pos_tag or "").strip().upper()
    if normalized_pos == "VERB" or (pos_code or "").strip().lower() == "vb":
        return WordTranslationFrame(kind="verb", text=f"at {normalized_lemma}")
    if normalized_pos == "NOUN" or (pos_code or "").strip().lower() == "sb":
        article = "et" if _is_neuter(gram=gram_or_function or "", morphology=morphology) else "en"
        return WordTranslationFrame(kind="noun", text=f"{article} {normalized_lemma}")
    if normalized_pos == "ADJ" or (pos_code or "").strip().lower() == "adj":
        return WordTranslationFrame(kind="adjective", text=f"en {normalized_lemma} ting")
    if normalized_pos == "ADV" or (pos_code or "").strip().lower() == "adv":
        return WordTranslationFrame(kind="adverb", text=f"han gør det {normalized_lemma}")
    if normalized_pos == "PRON" or (pos_code or "").strip().lower() == "pron":
        return WordTranslationFrame(kind="pronoun", text=f"{normalized_lemma} er her")
    if normalized_pos == "ADP" or (pos_code or "").strip().lower() in {"præp", "prp"}:
        return WordTranslationFrame(kind="preposition", text=f"{normalized_lemma} huset")
    if normalized_pos in {"CCONJ", "SCONJ"} or (pos_code or "").strip().lower() == "konj":
        return WordTranslationFrame(kind="conjunction", text=f"{normalized_lemma} jeg går")
    if normalized_pos == "DET" or (pos_code or "").strip().lower() == "art":
        return WordTranslationFrame(kind="article", text=f"{normalized_lemma} bog")
    if normalized_pos == "PROPN" or (pos_code or "").strip().lower() == "prop":
        return WordTranslationFrame(kind="proper_noun", text=f"navnet {normalized_lemma}")
    if normalized_pos == "NUM" or (pos_code or "").strip().lower() in {"talord", "num"}:
        return WordTranslationFrame(kind="numeral", text=f"{normalized_lemma} bøger")
    return WordTranslationFrame(kind="raw", text=normalized_lemma)


def cleanup_framed_word_translation(frame: WordTranslationFrame, translated: str | None) -> str | None:
    normalized = normalize_token(translated or "")
    if not normalized:
        return None

    if frame.kind == "raw":
        return _cleanup_raw(normalized)
    if frame.kind == "noun":
        return _cleanup_noun(normalized)
    if frame.kind == "verb":
        return _cleanup_verb(normalized)
    if frame.kind == "adjective":
        return _cleanup_adjective(normalized)
    if frame.kind == "adverb":
        return _cleanup_adverb(normalized)
    if frame.kind == "pronoun":
        return _cleanup_pronoun(normalized)
    if frame.kind == "preposition":
        return _cleanup_preposition(normalized)
    if frame.kind == "conjunction":
        return _cleanup_conjunction(normalized)
    if frame.kind == "article":
        return _cleanup_article(normalized)
    if frame.kind == "proper_noun":
        return _cleanup_proper_noun(normalized)
    if frame.kind == "numeral":
        return _cleanup_numeral(normalized)
    return _cleanup_raw(normalized)


def _cleanup_raw(value: str) -> str | None:
    if not _looks_like_english_phrase(value):
        return None
    return value


def _cleanup_noun(value: str) -> str | None:
    tokens = _split_tokens(value)
    tokens = _drop_leading_tokens(tokens, _LEADING_FUNCTION_TOKENS)
    if not tokens:
        return None
    candidate_tokens = _drop_trailing_tokens(tokens, _GENERIC_SUFFIX_NOUNS)
    if candidate_tokens:
        candidate = " ".join(candidate_tokens).strip()
        if candidate and _looks_like_english_phrase(candidate):
            return candidate
    for token in reversed(tokens):
        if token in _GENERIC_SUFFIX_NOUNS or token in _LEADING_FUNCTION_TOKENS:
            continue
        return token if _looks_like_english_phrase(token) else None
    return None


def _cleanup_verb(value: str) -> str | None:
    tokens = _split_tokens(value)
    tokens = _drop_leading_tokens(tokens, {"at", "that", "the"})
    if not tokens:
        return None
    # Strip a single leading "to" so we can re-add it cleanly, but keep
    # the rest intact so multi-word forms like "be called" are preserved.
    if tokens[0] == "to":
        tokens = tokens[1:]
    if not tokens:
        return None
    candidate = " ".join(tokens)
    if not _looks_like_english_phrase(candidate):
        return None
    return f"to {candidate}"


def _cleanup_adjective(value: str) -> str | None:
    tokens = _split_tokens(value)
    tokens = _drop_leading_tokens(tokens, _ARTICLE_TOKENS)
    tokens = _drop_trailing_tokens(tokens, _GENERIC_SUFFIX_NOUNS)
    candidate = " ".join(tokens).strip()
    if not candidate or not _looks_like_english_phrase(candidate):
        return None
    return candidate


_ADVERB_SUBJECT_VERB_SUFFIXES = (
    " does it",
    " does that",
    " does so",
    " do it",
    " do that",
)

_ADVERB_FRAME_PREFIXES = (
    "he does it ",
    "she does it ",
    "it happens ",
    "it is ",
    "he is ",
    "she is ",
    "they are ",
)


def _cleanup_adverb(value: str) -> str | None:
    candidate = value
    # Try stripping a leading template phrase ("he does it <adv>")
    for prefix in _ADVERB_FRAME_PREFIXES:
        if candidate.startswith(prefix):
            candidate = candidate[len(prefix) :].strip()
            break
    else:
        # Azure often reorders to natural English ("he <adv> does it").
        # Strip the trailing verb phrase to recover the adverb.
        for suffix in _ADVERB_SUBJECT_VERB_SUFFIXES:
            if candidate.endswith(suffix):
                # Drop "he " / "she " / "it " leading subject as well.
                trimmed = candidate[: -len(suffix)].strip()
                for subj in ("he ", "she ", "it ", "they "):
                    if trimmed.startswith(subj):
                        trimmed = trimmed[len(subj) :]
                        break
                candidate = trimmed
                break
    if not candidate or not _looks_like_english_phrase(candidate):
        return None
    return candidate


def _cleanup_pronoun(value: str) -> str | None:
    if value in _LEXICALIZED_PRONOUNS:
        return value
    tokens = _split_tokens(value)
    if not tokens:
        return None
    candidate = tokens[0]
    return candidate if _looks_like_english_phrase(candidate) else None


def _cleanup_preposition(value: str) -> str | None:
    if value in _LEXICALIZED_PREPOSITIONS:
        return value
    tokens = _split_tokens(value)
    if not tokens:
        return None
    if len(tokens) >= 3 and tokens[:3] == ["in", "front", "of"]:
        return "in front of"
    candidate = tokens[0]
    return candidate if _looks_like_english_phrase(candidate) else None


def _cleanup_conjunction(value: str) -> str | None:
    if value in _LEXICALIZED_CONJUNCTIONS:
        return value
    tokens = _split_tokens(value)
    if not tokens:
        return None
    candidate = tokens[0]
    return candidate if _looks_like_english_phrase(candidate) else None


def _cleanup_article(value: str) -> str | None:
    tokens = _split_tokens(value)
    if not tokens:
        return None
    candidate = tokens[0]
    if candidate not in _ARTICLE_TOKENS:
        return None
    return candidate


def _cleanup_proper_noun(value: str) -> str | None:
    tokens = _split_tokens(value)
    tokens = _drop_leading_tokens(tokens, {"called", "name", "named"})
    candidate = " ".join(tokens).strip()
    if not candidate or not _looks_like_english_phrase(candidate):
        return None
    return candidate


def _cleanup_numeral(value: str) -> str | None:
    tokens = _split_tokens(value)
    tokens = _drop_leading_tokens(tokens, _LEADING_FUNCTION_TOKENS)
    tokens = _drop_trailing_tokens(tokens, _COUNTED_SUFFIX_NOUNS | _GENERIC_SUFFIX_NOUNS)
    candidate = " ".join(tokens).strip()
    if not candidate or not _looks_like_english_phrase(candidate):
        return None
    return candidate


def _split_tokens(value: str) -> list[str]:
    return [token for token in value.split() if token]


def _drop_leading_tokens(tokens: list[str], removable: set[str]) -> list[str]:
    index = 0
    while index < len(tokens) and tokens[index] in removable:
        index += 1
    return tokens[index:]


def _drop_trailing_tokens(tokens: list[str], removable: set[str]) -> list[str]:
    end = len(tokens)
    while end > 0 and tokens[end - 1] in removable:
        end -= 1
    return tokens[:end]


def _looks_like_english_phrase(value: str) -> bool:
    normalized = normalize_token(value)
    if not normalized:
        return False
    if any(char in normalized for char in ("æ", "ø", "å")):
        return False
    if not _ALLOWED_CHARS_RE.fullmatch(normalized):
        return False
    tokens = normalized.split()
    if len(tokens) > 3:
        return False
    if len(tokens) > 1 and tokens[-1] in _SHORT_GENERIC_OBJECTS:
        return False
    return True


def _gram_pos_code(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if not normalized:
        return ""
    return normalized.split(".", 1)[0].strip()


def _is_neuter(*, gram: str, morphology: str | None) -> bool:
    if re.search(r"(^|\.)itk(\.|$)", gram):
        return True
    normalized_morphology = normalize_token(morphology or "")
    return "gender=neut" in normalized_morphology

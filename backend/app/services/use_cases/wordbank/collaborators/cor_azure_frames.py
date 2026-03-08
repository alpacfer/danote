from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class CORAzureFrame:
    kind: str
    text: str


def cor_local_azure_frame(entry: CORLocalEntry) -> CORAzureFrame:
    return _build_frame(
        lemma=entry.lemma,
        pos_code=_gram_pos_code(entry.gram_raw),
        gram_or_function=entry.gram_raw,
        morphology=entry.morphology,
    )


def cor_entry_azure_frame(entry: COREntry) -> CORAzureFrame:
    grammatical_function = entry.grammatical_function or ""
    pos_code = (entry.ordklasse or "").strip().lower() or _gram_pos_code(grammatical_function)
    return _build_frame(
        lemma=entry.lemma,
        pos_code=pos_code,
        gram_or_function=grammatical_function,
        morphology=entry.morphology,
    )


def azure_framed_translation_for_comparison(frame: CORAzureFrame, translated: str | None) -> str | None:
    normalized = normalize_token(translated or "")
    if not normalized:
        return None
    if frame.kind == "noun":
        return _strip_leading_english_article(normalized) or normalized
    if frame.kind == "verb":
        return _normalize_verb_infinitive(normalized)
    return normalized


def _build_frame(
    *,
    lemma: str,
    pos_code: str | None,
    gram_or_function: str | None,
    morphology: str | None,
) -> CORAzureFrame:
    normalized_lemma = normalize_token(lemma)
    if not normalized_lemma:
        return CORAzureFrame(kind="raw", text=lemma)

    pos = (pos_code or "").strip().lower()
    gram = (gram_or_function or "").strip().lower()
    if pos == "vb":
        return CORAzureFrame(kind="verb", text=f"at {normalized_lemma}")
    if pos == "sb":
        article = "et" if _is_neuter(gram=gram, morphology=morphology) else "en"
        return CORAzureFrame(kind="noun", text=f"{article} {normalized_lemma}")
    if pos == "adj":
        return CORAzureFrame(kind="adjective", text=f"en {normalized_lemma} ting")
    if pos == "adv":
        return CORAzureFrame(kind="adverb", text=f"han gør det {normalized_lemma}")
    if pos == "pron":
        return CORAzureFrame(kind="pronoun", text=f"{normalized_lemma} er her")
    if pos == "præp":
        return CORAzureFrame(kind="preposition", text=f"{normalized_lemma} huset")
    if pos == "konj":
        return CORAzureFrame(kind="conjunction", text=f"..., {normalized_lemma} jeg går")
    if pos == "art":
        return CORAzureFrame(kind="article", text=f"{normalized_lemma} bog")
    if pos == "prop":
        return CORAzureFrame(kind="proper_noun", text=f"navnet {normalized_lemma}")
    if pos == "talord":
        return CORAzureFrame(kind="numeral", text=f"{normalized_lemma} bøger")
    return CORAzureFrame(kind="raw", text=normalized_lemma)


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


def _strip_leading_english_article(value: str) -> str:
    return re.sub(r"^(?:a|an|the)\s+", "", value, flags=re.IGNORECASE).strip()


def _normalize_verb_infinitive(value: str) -> str:
    if not value:
        return value
    lowered = value.lower()
    if not lowered.startswith("to "):
        return value
    remainder = re.sub(r"^(?:to\s+)+", "", value, flags=re.IGNORECASE).strip()
    if not remainder:
        return "to"
    return f"to {remainder}"

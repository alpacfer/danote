from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class StaticHvWord:
    lemma: str
    english_translation: str
    pos_tag: str
    morphology: str
    example_source: str
    example_translation: str


STATIC_HV_WORDS: dict[str, StaticHvWord] = {
    "hvem": StaticHvWord("hvem", "who", "PRON", "PronType=Int", "hvem kommer i morgen?", "Who is coming tomorrow?"),
    "hvad": StaticHvWord("hvad", "what", "PRON", "PronType=Int|Gender=Neut", "hvad laver du?", "What are you doing?"),
    "hvilken": StaticHvWord("hvilken", "which", "DET", "PronType=Int|Number=Sing|Gender=Com", "hvilken bog læser du?", "Which book are you reading?"),
    "hvilket": StaticHvWord("hvilket", "which", "DET", "PronType=Int|Number=Sing|Gender=Neut", "hvilket tog tager vi?", "Which train are we taking?"),
    "hvilke": StaticHvWord("hvilke", "which", "DET", "PronType=Int|Number=Plur", "hvilke film kan du lide?", "Which movies do you like?"),
    "hvis": StaticHvWord("hvis", "whose", "DET", "PronType=Int|Poss=Yes", "hvis taske ligger her?", "Whose bag is here?"),
    "hvor": StaticHvWord("hvor", "where", "ADV", "PronType=Int", "hvor bor du?", "Where do you live?"),
    "hvornår": StaticHvWord("hvornår", "when", "ADV", "PronType=Int", "hvornår starter mødet?", "When does the meeting start?"),
    "hvordan": StaticHvWord("hvordan", "how", "ADV", "PronType=Int", "hvordan siger man det på dansk?", "How do you say that in Danish?"),
    "hvorfor": StaticHvWord("hvorfor", "why", "ADV", "PronType=Int", "hvorfor lærer du dansk?", "Why are you learning Danish?"),
}

STATIC_HV_WORDS_BY_ENGLISH: dict[str, StaticHvWord] = {
    "who": STATIC_HV_WORDS["hvem"],
    "what": STATIC_HV_WORDS["hvad"],
    "which": STATIC_HV_WORDS["hvilken"],
    "whose": STATIC_HV_WORDS["hvis"],
    "where": STATIC_HV_WORDS["hvor"],
    "when": STATIC_HV_WORDS["hvornår"],
    "how": STATIC_HV_WORDS["hvordan"],
    "why": STATIC_HV_WORDS["hvorfor"],
}


def static_hv_word_for_token(token: str | None) -> StaticHvWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_HV_WORDS.get(normalized)


def static_hv_word_for_english(token: str | None) -> StaticHvWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_HV_WORDS_BY_ENGLISH.get(normalized)

from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class StaticPronoun:
    lemma: str
    english_translation: str
    pos_tag: str
    morphology: str


STATIC_PRONOUNS: dict[str, StaticPronoun] = {
    "jeg": StaticPronoun("jeg", "I", "PRON", "PronType=Prs|Case=Nom|Person=1|Number=Sing"),
    "mig": StaticPronoun("mig", "me", "PRON", "PronType=Prs|Case=Acc|Person=1|Number=Sing"),
    "du": StaticPronoun("du", "you", "PRON", "PronType=Prs|Case=Nom|Person=2|Number=Sing"),
    "dig": StaticPronoun("dig", "you", "PRON", "PronType=Prs|Case=Acc|Person=2|Number=Sing"),
    "han": StaticPronoun("han", "he", "PRON", "PronType=Prs|Case=Nom|Person=3|Number=Sing|Gender=Masc"),
    "ham": StaticPronoun("ham", "him", "PRON", "PronType=Prs|Case=Acc|Person=3|Number=Sing|Gender=Masc"),
    "hun": StaticPronoun("hun", "she", "PRON", "PronType=Prs|Case=Nom|Person=3|Number=Sing|Gender=Fem"),
    "hende": StaticPronoun("hende", "her", "PRON", "PronType=Prs|Case=Acc|Person=3|Number=Sing|Gender=Fem"),
    "den": StaticPronoun("den", "it / that", "PRON", "PronType=Prs,Dem|Person=3|Number=Sing|Gender=Com"),
    "det": StaticPronoun("det", "it / that", "PRON", "PronType=Prs,Dem|Person=3|Number=Sing|Gender=Neut"),
    "sig": StaticPronoun("sig", "oneself", "PRON", "PronType=Prs|Reflex=Yes|Person=3"),
    "vi": StaticPronoun("vi", "we", "PRON", "PronType=Prs|Case=Nom|Person=1|Number=Plur"),
    "os": StaticPronoun("os", "us", "PRON", "PronType=Prs|Case=Acc|Person=1|Number=Plur"),
    "i": StaticPronoun("i", "you", "PRON", "PronType=Prs|Case=Nom|Person=2|Number=Plur"),
    "jer": StaticPronoun("jer", "you", "PRON", "PronType=Prs|Case=Acc|Person=2|Number=Plur"),
    "de": StaticPronoun("de", "they / those", "PRON", "PronType=Prs,Dem|Case=Nom|Person=3|Number=Plur"),
    "dem": StaticPronoun("dem", "them", "PRON", "PronType=Prs|Case=Acc|Person=3|Number=Plur"),
    "min": StaticPronoun("min", "my", "PRON", "PronType=Prs|Poss=Yes|Person=1|Number=Sing|Gender=Com"),
    "mit": StaticPronoun("mit", "my", "PRON", "PronType=Prs|Poss=Yes|Person=1|Number=Sing|Gender=Neut"),
    "mine": StaticPronoun("mine", "my", "PRON", "PronType=Prs|Poss=Yes|Person=1|Number=Plur"),
    "din": StaticPronoun("din", "your", "PRON", "PronType=Prs|Poss=Yes|Person=2|Number=Sing|Gender=Com"),
    "dit": StaticPronoun("dit", "your", "PRON", "PronType=Prs|Poss=Yes|Person=2|Number=Sing|Gender=Neut"),
    "dine": StaticPronoun("dine", "your", "PRON", "PronType=Prs|Poss=Yes|Person=2|Number=Plur"),
    "hans": StaticPronoun("hans", "his", "PRON", "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Masc"),
    "hendes": StaticPronoun("hendes", "her", "PRON", "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Fem"),
    "dens": StaticPronoun("dens", "its", "PRON", "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Com"),
    "dets": StaticPronoun("dets", "its", "PRON", "PronType=Prs|Poss=Yes|Person=3|Number=Sing|Gender=Neut"),
    "sin": StaticPronoun("sin", "one's own", "PRON", "PronType=Prs|Poss=Yes|Reflex=Yes|Gender=Com"),
    "sit": StaticPronoun("sit", "one's own", "PRON", "PronType=Prs|Poss=Yes|Reflex=Yes|Gender=Neut"),
    "sine": StaticPronoun("sine", "one's own", "PRON", "PronType=Prs|Poss=Yes|Reflex=Yes|Number=Plur"),
    "vores": StaticPronoun("vores", "our", "PRON", "PronType=Prs|Poss=Yes|Person=1|Number=Plur"),
    "jeres": StaticPronoun("jeres", "your", "PRON", "PronType=Prs|Poss=Yes|Person=2|Number=Plur"),
    "deres": StaticPronoun("deres", "their", "PRON", "PronType=Prs|Poss=Yes|Person=3|Number=Plur"),
    "denne": StaticPronoun("denne", "this", "PRON", "PronType=Dem|Number=Sing|Gender=Com"),
    "dette": StaticPronoun("dette", "this", "PRON", "PronType=Dem|Number=Sing|Gender=Neut"),
    "disse": StaticPronoun("disse", "these", "PRON", "PronType=Dem|Number=Plur"),
    "hvem": StaticPronoun("hvem", "who", "PRON", "PronType=Int"),
    "hvad": StaticPronoun("hvad", "what", "PRON", "PronType=Int|Gender=Neut"),
    # Interrogative which/whose modify nouns → DET (matches static_hv_words.py and UD-DA).
    "hvilken": StaticPronoun("hvilken", "which", "DET", "PronType=Int|Number=Sing|Gender=Com"),
    "hvilket": StaticPronoun("hvilket", "which", "DET", "PronType=Int|Number=Sing|Gender=Neut"),
    "hvilke": StaticPronoun("hvilke", "which", "DET", "PronType=Int|Number=Plur"),
    "hvis": StaticPronoun("hvis", "whose", "DET", "PronType=Int,Rel|Poss=Yes"),
    "som": StaticPronoun("som", "who / which / that", "PRON", "PronType=Rel"),
    "der": StaticPronoun("der", "who / which", "PRON", "PronType=Rel"),
    "man": StaticPronoun("man", "one / you", "PRON", "PronType=Ind|Person=3|Number=Sing"),
    "nogen": StaticPronoun("nogen", "someone / any", "PRON", "PronType=Ind|Gender=Com"),
    "noget": StaticPronoun("noget", "something / any", "PRON", "PronType=Ind|Gender=Neut"),
    "ingen": StaticPronoun("ingen", "no one / none", "PRON", "PronType=Neg|Gender=Com"),
    "intet": StaticPronoun("intet", "nothing / none", "PRON", "PronType=Neg|Gender=Neut"),
    "alle": StaticPronoun("alle", "all / everyone", "PRON", "PronType=Tot|Number=Plur"),
    "enhver": StaticPronoun("enhver", "each / every", "PRON", "PronType=Tot|Gender=Com"),
    "ethvert": StaticPronoun("ethvert", "each / every", "PRON", "PronType=Tot|Gender=Neut"),
    "begge": StaticPronoun("begge", "both", "PRON", "PronType=Tot|Number=Plur"),
    "hinanden": StaticPronoun("hinanden", "each other", "PRON", "PronType=Rcp"),
    "hverandre": StaticPronoun("hverandre", "each other", "PRON", "PronType=Rcp"),
    "andre": StaticPronoun("andre", "others / other", "PRON", "PronType=Ind|Number=Plur"),
    "selv": StaticPronoun("selv", "self / oneself", "PRON", "PronType=Emp"),
}

STATIC_PRONOUNS_BY_ENGLISH: dict[str, StaticPronoun] = {
    "i": STATIC_PRONOUNS["jeg"],
    "me": STATIC_PRONOUNS["mig"],
    "you": STATIC_PRONOUNS["du"],
    "he": STATIC_PRONOUNS["han"],
    "him": STATIC_PRONOUNS["ham"],
    "she": STATIC_PRONOUNS["hun"],
    "her": STATIC_PRONOUNS["hende"],
    "it": STATIC_PRONOUNS["det"],
    "oneself": STATIC_PRONOUNS["sig"],
    "we": STATIC_PRONOUNS["vi"],
    "us": STATIC_PRONOUNS["os"],
    "they": STATIC_PRONOUNS["de"],
    "them": STATIC_PRONOUNS["dem"],
    "my": STATIC_PRONOUNS["min"],
    "your": STATIC_PRONOUNS["din"],
    "his": STATIC_PRONOUNS["hans"],
    "its": STATIC_PRONOUNS["dets"],
    "our": STATIC_PRONOUNS["vores"],
    "their": STATIC_PRONOUNS["deres"],
    "this": STATIC_PRONOUNS["denne"],
    "these": STATIC_PRONOUNS["disse"],
    "that": STATIC_PRONOUNS["den"],
    "those": STATIC_PRONOUNS["de"],
    "who": STATIC_PRONOUNS["hvem"],
    "what": STATIC_PRONOUNS["hvad"],
    "which": STATIC_PRONOUNS["hvilken"],
    "whose": STATIC_PRONOUNS["hvis"],
    "one": STATIC_PRONOUNS["man"],
    "someone": STATIC_PRONOUNS["nogen"],
    "something": STATIC_PRONOUNS["noget"],
    "any": STATIC_PRONOUNS["nogen"],
    "no one": STATIC_PRONOUNS["ingen"],
    "none": STATIC_PRONOUNS["ingen"],
    "nothing": STATIC_PRONOUNS["intet"],
    "all": STATIC_PRONOUNS["alle"],
    "everyone": STATIC_PRONOUNS["alle"],
    "each": STATIC_PRONOUNS["enhver"],
    "every": STATIC_PRONOUNS["enhver"],
    "both": STATIC_PRONOUNS["begge"],
    "each other": STATIC_PRONOUNS["hinanden"],
    "others": STATIC_PRONOUNS["andre"],
    "self": STATIC_PRONOUNS["selv"],
}


def static_pronoun_for_token(token: str | None) -> StaticPronoun | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRONOUNS.get(normalized)


def static_pronoun_for_english(token: str | None) -> StaticPronoun | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRONOUNS_BY_ENGLISH.get(normalized)

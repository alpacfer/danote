from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class StaticPresavedWord:
    lemma: str
    english_translation: str
    pos_tag: str | None = None
    morphology: str | None = None
    meaning_key: str | None = None


STATIC_PRESAVED_WORDS: dict[str, StaticPresavedWord] = {
    "ikke": StaticPresavedWord("ikke", "not", "ADV"),
    "er": StaticPresavedWord("være", "to be / is / are", "AUX"),
    "i": StaticPresavedWord("i", "in / for", "ADP"),
    "der": StaticPresavedWord("der", "there", "ADV", meaning_key="there"),
    "en": StaticPresavedWord("en", "a / an", "DET", "Gender=Com|Number=Sing", meaning_key="article"),
    "et": StaticPresavedWord("et", "a / an", "DET", "Gender=Neut|Number=Sing", meaning_key="article"),
    "-en": StaticPresavedWord("-en", "the", "DET", "Gender=Com|Number=Sing"),
    "-et": StaticPresavedWord("-et", "the", "DET", "Gender=Neut|Number=Sing"),
    "-ne": StaticPresavedWord("-ne", "the", "DET", "Number=Plur"),
    "hvis": StaticPresavedWord("hvis", "whose / if", "SCONJ"),
    "for": StaticPresavedWord("for", "for / because", "ADP"),
    "før": StaticPresavedWord("før", "before", "ADP"),
    "på": StaticPresavedWord("på", "on / at", "ADP"),
    "til": StaticPresavedWord("til", "to / for", "ADP"),
    "fra": StaticPresavedWord("fra", "from", "ADP"),
    "med": StaticPresavedWord("med", "with", "ADP"),
    "af": StaticPresavedWord("af", "of / by / off", "ADP"),
    "over": StaticPresavedWord("over", "over / above", "ADP"),
    "under": StaticPresavedWord("under", "under / during", "ADP"),
    "om": StaticPresavedWord("om", "about / in", "ADP"),
    "hos": StaticPresavedWord("hos", "at someone's place", "ADP"),
    "ved": StaticPresavedWord("ved", "by / next to", "ADP"),
    "mod": StaticPresavedWord("mod", "against / toward", "ADP"),
    "gennem": StaticPresavedWord("gennem", "through", "ADP"),
    "efter": StaticPresavedWord("efter", "after", "ADP"),
    "mellem": StaticPresavedWord("mellem", "between", "ADP"),
    "uden": StaticPresavedWord("uden", "without", "ADP"),
    "bag": StaticPresavedWord("bag", "behind", "ADP"),
    "foran": StaticPresavedWord("foran", "in front of", "ADP"),
    "omkring": StaticPresavedWord("omkring", "around / about", "ADP"),
    "og": StaticPresavedWord("og", "and", "CCONJ"),
    "eller": StaticPresavedWord("eller", "or", "CCONJ"),
    "men": StaticPresavedWord("men", "but", "CCONJ"),
    "så": StaticPresavedWord("så", "so", "CCONJ"),
    "at": StaticPresavedWord("at", "that", "SCONJ"),
    "fordi": StaticPresavedWord("fordi", "because", "SCONJ"),
    "når": StaticPresavedWord("når", "when", "SCONJ"),
    "da": StaticPresavedWord("da", "when / since", "SCONJ"),
    "mens": StaticPresavedWord("mens", "while", "SCONJ"),
    "selvom": StaticPresavedWord("selvom", "although / even though", "SCONJ"),
    "inden": StaticPresavedWord("inden", "before", "SCONJ"),
    "end": StaticPresavedWord("end", "than", "SCONJ"),
    "skønt": StaticPresavedWord("skønt", "although / even though", "SCONJ"),
    "ligesom": StaticPresavedWord("ligesom", "just as / like", "SCONJ"),
    "nul": StaticPresavedWord("nul", "zero", "NUM", meaning_key="number"),
    "to": StaticPresavedWord("to", "two", "NUM", meaning_key="number"),
    "tre": StaticPresavedWord("tre", "three", "NUM", meaning_key="number"),
    "fire": StaticPresavedWord("fire", "four", "NUM", meaning_key="number"),
    "fem": StaticPresavedWord("fem", "five", "NUM", meaning_key="number"),
    "seks": StaticPresavedWord("seks", "six", "NUM", meaning_key="number"),
    "syv": StaticPresavedWord("syv", "seven", "NUM", meaning_key="number"),
    "otte": StaticPresavedWord("otte", "eight", "NUM", meaning_key="number"),
    "ni": StaticPresavedWord("ni", "nine", "NUM", meaning_key="number"),
    "ti": StaticPresavedWord("ti", "ten", "NUM", meaning_key="number"),
    "elleve": StaticPresavedWord("elleve", "eleven", "NUM", meaning_key="number"),
    "tolv": StaticPresavedWord("tolv", "twelve", "NUM", meaning_key="number"),
    "tretten": StaticPresavedWord("tretten", "thirteen", "NUM", meaning_key="number"),
    "fjorten": StaticPresavedWord("fjorten", "fourteen", "NUM", meaning_key="number"),
    "femten": StaticPresavedWord("femten", "fifteen", "NUM", meaning_key="number"),
    "seksten": StaticPresavedWord("seksten", "sixteen", "NUM", meaning_key="number"),
    "sytten": StaticPresavedWord("sytten", "seventeen", "NUM", meaning_key="number"),
    "atten": StaticPresavedWord("atten", "eighteen", "NUM", meaning_key="number"),
    "nitten": StaticPresavedWord("nitten", "nineteen", "NUM", meaning_key="number"),
    "tyve": StaticPresavedWord("tyve", "twenty", "NUM", meaning_key="number"),
    "tredive": StaticPresavedWord("tredive", "thirty", "NUM", meaning_key="number"),
    "fyrre": StaticPresavedWord("fyrre", "forty", "NUM", meaning_key="number"),
    "halvtreds": StaticPresavedWord("halvtreds", "fifty", "NUM", meaning_key="number"),
    "tres": StaticPresavedWord("tres", "sixty", "NUM", meaning_key="number"),
    "halvfjerds": StaticPresavedWord("halvfjerds", "seventy", "NUM", meaning_key="number"),
    "firs": StaticPresavedWord("firs", "eighty", "NUM", meaning_key="number"),
    "halvfems": StaticPresavedWord("halvfems", "ninety", "NUM", meaning_key="number"),
    "første": StaticPresavedWord("første", "first", "ADJ"),
    "anden": StaticPresavedWord("anden", "second", "ADJ"),
    "tredje": StaticPresavedWord("tredje", "third", "ADJ"),
    "fjerde": StaticPresavedWord("fjerde", "fourth", "ADJ"),
    "femte": StaticPresavedWord("femte", "fifth", "ADJ"),
    "sjette": StaticPresavedWord("sjette", "sixth", "ADJ"),
    "syvende": StaticPresavedWord("syvende", "seventh", "ADJ"),
    "ottende": StaticPresavedWord("ottende", "eighth", "ADJ"),
    "niende": StaticPresavedWord("niende", "ninth", "ADJ"),
    "tiende": StaticPresavedWord("tiende", "tenth", "ADJ"),
    "ellevte": StaticPresavedWord("ellevte", "eleventh", "ADJ"),
    "tolvte": StaticPresavedWord("tolvte", "twelfth", "ADJ"),
    "trettende": StaticPresavedWord("trettende", "thirteenth", "ADJ"),
    "tyvende": StaticPresavedWord("tyvende", "twentieth", "ADJ"),
    "tredivte": StaticPresavedWord("tredivte", "thirtieth", "ADJ"),
    "hundrede": StaticPresavedWord("hundrede", "hundred / hundredth", "NUM"),
    "tusinde": StaticPresavedWord("tusinde", "thousandth", "ADJ"),
    "mandag": StaticPresavedWord("mandag", "Monday", "NOUN"),
    "tirsdag": StaticPresavedWord("tirsdag", "Tuesday", "NOUN"),
    "onsdag": StaticPresavedWord("onsdag", "Wednesday", "NOUN"),
    "torsdag": StaticPresavedWord("torsdag", "Thursday", "NOUN"),
    "fredag": StaticPresavedWord("fredag", "Friday", "NOUN"),
    "lørdag": StaticPresavedWord("lørdag", "Saturday", "NOUN"),
    "søndag": StaticPresavedWord("søndag", "Sunday", "NOUN"),
    "januar": StaticPresavedWord("januar", "January", "NOUN"),
    "februar": StaticPresavedWord("februar", "February", "NOUN"),
    "marts": StaticPresavedWord("marts", "March", "NOUN"),
    "april": StaticPresavedWord("april", "April", "NOUN"),
    "maj": StaticPresavedWord("maj", "May", "NOUN"),
    "juni": StaticPresavedWord("juni", "June", "NOUN"),
    "juli": StaticPresavedWord("juli", "July", "NOUN"),
    "august": StaticPresavedWord("august", "August", "NOUN"),
    "september": StaticPresavedWord("september", "September", "NOUN"),
    "oktober": StaticPresavedWord("oktober", "October", "NOUN"),
    "november": StaticPresavedWord("november", "November", "NOUN"),
    "december": StaticPresavedWord("december", "December", "NOUN"),
}

STATIC_PRESAVED_SENSES_BY_TOKEN: dict[str, tuple[StaticPresavedWord, ...]] = {
    "der": (
        STATIC_PRESAVED_WORDS["der"],
    ),
    "en": (
        STATIC_PRESAVED_WORDS["en"],
        StaticPresavedWord("en", "one", "NUM", meaning_key="number"),
    ),
    "et": (
        STATIC_PRESAVED_WORDS["et"],
        StaticPresavedWord("et", "one", "NUM", meaning_key="number"),
    ),
    "for": (
        StaticPresavedWord("for", "for", "ADP", meaning_key="preposition"),
        StaticPresavedWord("for", "because", "CCONJ", meaning_key="conjunction"),
    ),
    "før": (
        StaticPresavedWord("før", "before", "ADP", meaning_key="preposition"),
        StaticPresavedWord("før", "before", "SCONJ", meaning_key="conjunction"),
    ),
}

STATIC_PRESAVED_WORDS_BY_ENGLISH: dict[str, StaticPresavedWord] = {}
# Two-pass build so an exact translation match always wins over a slash-split
# partial. Otherwise "because" would resolve to "for" (translation "for /
# because") and shadow the canonical "fordi" (translation "because") just
# because "for" sits earlier in the dict iteration order.
for word in STATIC_PRESAVED_WORDS.values():
    normalized_full = normalize_token(word.english_translation)
    if normalized_full:
        STATIC_PRESAVED_WORDS_BY_ENGLISH.setdefault(normalized_full, word)
for word in STATIC_PRESAVED_WORDS.values():
    for part in word.english_translation.replace("(", "/").replace(")", "").split("/"):
        normalized_part = normalize_token(part)
        if normalized_part:
            if normalized_part == "is":
                continue
            STATIC_PRESAVED_WORDS_BY_ENGLISH.setdefault(normalized_part, word)


def static_presaved_word_for_token(token: str | None) -> StaticPresavedWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRESAVED_WORDS.get(normalized)


def static_presaved_words_for_token(token: str | None) -> tuple[StaticPresavedWord, ...]:
    normalized = normalize_token(token or "")
    if not normalized:
        return ()
    if normalized in STATIC_PRESAVED_SENSES_BY_TOKEN:
        return STATIC_PRESAVED_SENSES_BY_TOKEN[normalized]
    word = STATIC_PRESAVED_WORDS.get(normalized)
    return (word,) if word is not None else ()


def static_presaved_word_for_english(token: str | None) -> StaticPresavedWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRESAVED_WORDS_BY_ENGLISH.get(normalized)

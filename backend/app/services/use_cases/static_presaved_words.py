from __future__ import annotations

from dataclasses import dataclass

from app.services.token_classifier import normalize_token


@dataclass(frozen=True, slots=True)
class StaticPresavedWord:
    lemma: str
    english_translation: str
    pos_tag: str | None = None
    morphology: str | None = None


STATIC_PRESAVED_WORDS: dict[str, StaticPresavedWord] = {
    "i": StaticPresavedWord("i", "in / for", "ADP"),
    "en": StaticPresavedWord("en", "one / a", "NUM"),
    "et": StaticPresavedWord("et", "one / a", "NUM"),
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
    "nul": StaticPresavedWord("nul", "0", "NUM"),
    "to": StaticPresavedWord("to", "2", "NUM"),
    "tre": StaticPresavedWord("tre", "3", "NUM"),
    "fire": StaticPresavedWord("fire", "4", "NUM"),
    "fem": StaticPresavedWord("fem", "5", "NUM"),
    "seks": StaticPresavedWord("seks", "6", "NUM"),
    "syv": StaticPresavedWord("syv", "7", "NUM"),
    "otte": StaticPresavedWord("otte", "8", "NUM"),
    "ni": StaticPresavedWord("ni", "9", "NUM"),
    "ti": StaticPresavedWord("ti", "10", "NUM"),
    "elleve": StaticPresavedWord("elleve", "11", "NUM"),
    "tolv": StaticPresavedWord("tolv", "12", "NUM"),
    "tretten": StaticPresavedWord("tretten", "13", "NUM"),
    "fjorten": StaticPresavedWord("fjorten", "14", "NUM"),
    "femten": StaticPresavedWord("femten", "15", "NUM"),
    "seksten": StaticPresavedWord("seksten", "16", "NUM"),
    "sytten": StaticPresavedWord("sytten", "17", "NUM"),
    "atten": StaticPresavedWord("atten", "18", "NUM"),
    "nitten": StaticPresavedWord("nitten", "19", "NUM"),
    "tyve": StaticPresavedWord("tyve", "20", "NUM"),
    "tredive": StaticPresavedWord("tredive", "30", "NUM"),
    "fyrre": StaticPresavedWord("fyrre", "40", "NUM"),
    "halvtreds": StaticPresavedWord("halvtreds", "50", "NUM"),
    "tres": StaticPresavedWord("tres", "60", "NUM"),
    "halvfjerds": StaticPresavedWord("halvfjerds", "70", "NUM"),
    "firs": StaticPresavedWord("firs", "80", "NUM"),
    "halvfems": StaticPresavedWord("halvfems", "90", "NUM"),
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
    "forår": StaticPresavedWord("forår", "spring", "NOUN"),
    "sommer": StaticPresavedWord("sommer", "summer", "NOUN"),
    "efterår": StaticPresavedWord("efterår", "autumn / fall", "NOUN"),
    "vinter": StaticPresavedWord("vinter", "winter", "NOUN"),
    "altid": StaticPresavedWord("altid", "always", "ADV"),
    "ofte": StaticPresavedWord("ofte", "often", "ADV"),
    "sjældent": StaticPresavedWord("sjældent", "rarely", "ADV"),
    "aldrig": StaticPresavedWord("aldrig", "never", "ADV"),
    "indtil": StaticPresavedWord("indtil", "until", "ADP"),
    "siden": StaticPresavedWord("siden", "since", "ADP"),
}

STATIC_PRESAVED_WORDS_BY_ENGLISH: dict[str, StaticPresavedWord] = {}
for word in STATIC_PRESAVED_WORDS.values():
    for part in word.english_translation.replace("(", "/").replace(")", "").split("/"):
        normalized_part = normalize_token(part)
        if normalized_part:
            STATIC_PRESAVED_WORDS_BY_ENGLISH.setdefault(normalized_part, word)


def static_presaved_word_for_token(token: str | None) -> StaticPresavedWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRESAVED_WORDS.get(normalized)


def static_presaved_word_for_english(token: str | None) -> StaticPresavedWord | None:
    normalized = normalize_token(token or "")
    if not normalized:
        return None
    return STATIC_PRESAVED_WORDS_BY_ENGLISH.get(normalized)

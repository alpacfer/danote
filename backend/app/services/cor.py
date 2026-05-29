from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from urllib.parse import quote

import httpx


def _normalize_space(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return " ".join(value.strip().split())


def _normalize_status(value: str | None) -> str | None:
    cleaned = _normalize_space(value).upper()
    if cleaned in {"N", "U", "K"}:
        return cleaned
    return None


_ORDKLASSE_TO_UD_POS = {
    "adj": "ADJ",
    "adv": "ADV",
    "art": "DET",
    "fork": "X",
    "interj": "INTJ",
    "konj": "CCONJ",
    "num": "NUM",
    "part": "PART",
    "pron": "PRON",
    "prp": "ADP",
    "præp": "ADP",
    "sb": "NOUN",
    "vb": "VERB",
}

_GRAMMATISK_TO_UD_FEATURES = {
    "akt": ("Voice=Act",),
    "best": ("Definite=Def",),
    "f": ("Gender=Fem",),
    "fk": ("Gender=Com",),
    "gen": ("Case=Gen",),
    "imp": ("Mood=Imp", "VerbForm=Fin"),
    "itk": ("Gender=Neut",),
    "kompar": ("Degree=Cmp",),
    "m": ("Gender=Masc",),
    "part": ("VerbForm=Part",),
    "pass": ("Voice=Pass",),
    "pl": ("Number=Plur",),
    "pos": ("Degree=Pos",),
    "prs": ("Tense=Pres", "VerbForm=Fin"),
    "præs": ("Tense=Pres", "VerbForm=Fin"),
    "præt": ("Tense=Past", "VerbForm=Fin"),
    "sg": ("Number=Sing",),
    "superl": ("Degree=Sup",),
    "ubest": ("Definite=Ind",),
}


@dataclass(frozen=True)
class COREntry:
    cor_id: str
    lemma: str
    full_form: str
    ordklasse: str | None
    grammatical_function: str | None
    glosse: str | None
    norm_status: str | None
    pos_tag: str | None
    morphology: str | None


@dataclass
class CORLexiconService:
    base_url: str = "https://ordregister.dk"
    register: str = "COR"
    timeout_seconds: float = 4.0
    max_cache_entries: int = 2048
    provider: str = field(default="cor", init=False)
    _client: httpx.Client | None = field(default=None, init=False, repr=False, compare=False)
    _cache: OrderedDict[tuple[str, str], tuple[COREntry, ...]] = field(
        default_factory=OrderedDict, init=False, repr=False, compare=False
    )

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(base_url=self.base_url.rstrip("/"), timeout=self.timeout_seconds)
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def lookup_full_form(self, value: str) -> list[COREntry]:
        return list(self._lookup(column="fuldform", value=value))

    def lookup_lemma(self, value: str) -> list[COREntry]:
        return list(self._lookup(column="lemma", value=value))

    def _lookup(self, *, column: str, value: str) -> tuple[COREntry, ...]:
        normalized_value = _normalize_space(value).lower()
        if not normalized_value:
            return ()

        cache_key = (column, normalized_value)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache.move_to_end(cache_key)
            return cached

        encoded_value = quote(normalized_value, safe="")
        path = f"/{column}/{self.register}/json/{encoded_value}"
        try:
            response = self._ensure_client().get(path)
            response.raise_for_status()
            payload = response.json()
        except Exception:
            self._remember(cache_key, ())
            return ()

        rows = payload.get("svar") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            self._remember(cache_key, ())
            return ()

        parsed: list[COREntry] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            cor_id = _normalize_space(row.get("COR-id"))
            lemma = _normalize_space(row.get("lemma")).lower()
            full_form = _normalize_space(row.get("fuldform")).lower()
            ordklasse = _normalize_space(row.get("ordklasse")).lower() or None
            grammatical_function = _normalize_space(row.get("grammatisk function")).lower() or None
            glosse = _normalize_space(row.get("glosse")) or None
            norm_status = _normalize_status(row.get("normeret"))
            if not cor_id or not lemma or not full_form:
                continue
            pos_tag = _to_ud_pos(ordklasse, grammatical_function)
            morphology = _to_ud_morphology(grammatical_function)
            parsed.append(
                COREntry(
                    cor_id=cor_id,
                    lemma=lemma,
                    full_form=full_form,
                    ordklasse=ordklasse,
                    grammatical_function=grammatical_function,
                    glosse=glosse,
                    norm_status=norm_status,
                    pos_tag=pos_tag,
                    morphology=morphology,
                )
            )

        result = tuple(parsed)
        self._remember(cache_key, result)
        return result

    def _remember(self, key: tuple[str, str], value: tuple[COREntry, ...]) -> None:
        self._cache[key] = value
        self._cache.move_to_end(key)
        while len(self._cache) > self.max_cache_entries:
            self._cache.popitem(last=False)


def _to_ud_pos(ordklasse: str | None, grammatical_function: str | None) -> str | None:
    if ordklasse in _ORDKLASSE_TO_UD_POS:
        return _ORDKLASSE_TO_UD_POS[ordklasse]
    if isinstance(grammatical_function, str) and "." in grammatical_function:
        first = grammatical_function.split(".", 1)[0]
        return _ORDKLASSE_TO_UD_POS.get(first)
    return None


def _to_ud_morphology(grammatical_function: str | None) -> str | None:
    if not isinstance(grammatical_function, str) or not grammatical_function:
        return None

    features: list[str] = []
    for chunk in grammatical_function.split("."):
        mapped = _GRAMMATISK_TO_UD_FEATURES.get(chunk)
        if mapped is None:
            continue
        for feature in mapped:
            if feature not in features:
                features.append(feature)

    if not features:
        return None
    return "|".join(features)

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3


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
    "inf": ("VerbForm=Inf",),
    "itk": ("Gender=Neut",),
    "kompar": ("Degree=Cmp",),
    "m": ("Gender=Masc",),
    "part": ("VerbForm=Part",),
    "pass": ("Voice=Pass",),
    "perf": ("Aspect=Perf",),
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
class CORLocalEntry:
    cor_id: str
    lemma: str
    gloss: str | None
    gram_raw: str
    form: str
    norm: str | None
    lemma_idx: int
    gram_code: int
    variation: int
    pos_tag: str | None
    morphology: str | None
    features: dict[str, str]
    extra_tags: list[str]


def decode_gram(gram_raw: str) -> tuple[str | None, str | None, dict[str, str], list[str]]:
    normalized = _normalize_space(gram_raw).lower()
    if not normalized:
        return None, None, {}, []

    chunks = [chunk for chunk in normalized.split(".") if chunk]
    if not chunks:
        return None, None, {}, []

    pos_tag = _ORDKLASSE_TO_UD_POS.get(chunks[0])
    feature_pairs: list[tuple[str, str]] = []
    extra_tags: list[str] = []
    for index, chunk in enumerate(chunks):
        mapped = _GRAMMATISK_TO_UD_FEATURES.get(chunk)
        if mapped is None:
            # Preserve unknown grammatical markers so UI/debug can still expose them.
            if index > 0 or pos_tag is None:
                extra_tags.append(chunk)
            continue
        for feature in mapped:
            if "=" not in feature:
                continue
            key, value = feature.split("=", 1)
            feature_pairs.append((key, value))

    features: dict[str, str] = {}
    for key, value in feature_pairs:
        if key not in features:
            features[key] = value

    morphology = "|".join(f"{key}={value}" for key, value in features.items()) or None
    return pos_tag, morphology, features, extra_tags


@dataclass
class CORLocalLexiconService:
    db_path: Path
    provider: str = "cor_local"
    _unique_lemmas: frozenset[str] | None = field(default=None, init=False, repr=False)

    @property
    def unique_lemmas(self) -> frozenset[str]:
        if self._unique_lemmas is None:
            rows = self._query_rows(
                "SELECT DISTINCT lower(lemma) AS lemma FROM cor_entries WHERE norm = 'N'",
                (),
            )
            self._unique_lemmas = frozenset(str(row["lemma"]) for row in rows)
        return self._unique_lemmas

    def lookup_form(self, value: str, limit: int = 100) -> list[CORLocalEntry]:
        normalized_value = _normalize_space(value)
        if not normalized_value:
            return []

        exact_rows = self._query_rows(
            """
            SELECT
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            FROM cor_entries
            WHERE form = ?
            ORDER BY
                CASE norm WHEN 'N' THEN 0 WHEN 'K' THEN 1 WHEN 'U' THEN 2 ELSE 3 END,
                lemma_idx,
                gram_code,
                variation,
                cor_id
            LIMIT ?
            """,
            (normalized_value, limit),
        )
        if exact_rows:
            return [self._row_to_entry(row) for row in exact_rows]

        normalized_lower = normalized_value.lower()
        lowered_rows = self._query_rows(
            """
            SELECT
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            FROM cor_entries
            WHERE form = ?
            ORDER BY
                CASE norm WHEN 'N' THEN 0 WHEN 'K' THEN 1 WHEN 'U' THEN 2 ELSE 3 END,
                lemma_idx,
                gram_code,
                variation,
                cor_id
            LIMIT ?
            """,
            (normalized_lower, limit),
        )
        if lowered_rows:
            return [self._row_to_entry(row) for row in lowered_rows]

        fallback_rows = self._query_rows(
            """
            SELECT
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            FROM cor_entries
            WHERE lower(form) = lower(?)
            ORDER BY
                CASE norm WHEN 'N' THEN 0 WHEN 'K' THEN 1 WHEN 'U' THEN 2 ELSE 3 END,
                lemma_idx,
                gram_code,
                variation,
                cor_id
            LIMIT ?
            """,
            (normalized_value, limit),
        )
        return [self._row_to_entry(row) for row in fallback_rows]

    def lookup_lemma(self, lemma_idx: int, limit: int = 1000) -> list[CORLocalEntry]:
        if lemma_idx < 1:
            return []
        rows = self._query_rows(
            """
            SELECT
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            FROM cor_entries
            WHERE lemma_idx = ?
            ORDER BY
                CASE norm WHEN 'N' THEN 0 WHEN 'K' THEN 1 WHEN 'U' THEN 2 ELSE 3 END,
                lemma_idx,
                gram_code,
                variation,
                cor_id
            LIMIT ?
            """,
            (lemma_idx, limit),
        )
        return [self._row_to_entry(row) for row in rows]

    def lookup_cor_id(self, cor_id: str) -> CORLocalEntry | None:
        normalized_cor_id = _normalize_space(cor_id)
        if not normalized_cor_id:
            return None
        rows = self._query_rows(
            """
            SELECT
                cor_id, lemma, gloss, gram, form, norm, lemma_idx, gram_code, variation
            FROM cor_entries
            WHERE cor_id = ?
            LIMIT 1
            """,
            (normalized_cor_id,),
        )
        if not rows:
            return None
        return self._row_to_entry(rows[0])

    def _query_rows(
        self,
        sql: str,
        params: tuple[object, ...],
    ) -> list[sqlite3.Row]:
        if not self.db_path.exists():
            raise FileNotFoundError(f"COR local database not found at {self.db_path}")
        with self._connect_read_only() as conn:
            return conn.execute(sql, params).fetchall()

    def _connect_read_only(self) -> sqlite3.Connection:
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        return conn

    def _row_to_entry(self, row: sqlite3.Row) -> CORLocalEntry:
        gram_raw = _normalize_space(row["gram"])
        pos_tag, morphology, features, extra_tags = decode_gram(gram_raw)
        return CORLocalEntry(
            cor_id=row["cor_id"],
            lemma=_normalize_space(row["lemma"]).lower(),
            gloss=_normalize_space(row["gloss"]) or None,
            gram_raw=gram_raw,
            form=_normalize_space(row["form"]).lower(),
            norm=_normalize_status(row["norm"]),
            lemma_idx=int(row["lemma_idx"]),
            gram_code=int(row["gram_code"]),
            variation=int(row["variation"]),
            pos_tag=pos_tag,
            morphology=morphology,
            features=features,
            extra_tags=extra_tags,
        )

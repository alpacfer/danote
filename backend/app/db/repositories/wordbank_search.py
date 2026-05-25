from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterable

_PREFIX_MIN_LENGTH = 3
_ENGLISH_ARTICLE_PREFIXES = ("to ", "a ", "an ", "the ")
_DANISH_ARTICLE_PREFIXES = ("at ", "den ", "det ", "en ", "et ")
_TOKEN_SPLIT = re.compile(r"[\s\-_/]+")
_WORD_CHAR_RE = re.compile(r"[^\w\s]", re.UNICODE)
_ENGLISH_SUFFIXES = ("ies", "es", "ed", "ing", "s")


def search_lemmas(
    conn: sqlite3.Connection,
    normalized_query: str,
    *,
    limit: int,
    owner_user_id: int,
) -> list[sqlite3.Row]:
    """FTS5-backed saved-wordbank search.

    Matches against lemma, Danish gloss, primary English translation,
    descriptive english_gloss, alternative English translations, and
    inflection surface forms. Each returned row carries ``matched_via``
    explaining which field triggered the hit.

    FTS5 only matches whole tokens (after Porter stemming). To preserve
    user-typed substrings of inflections — e.g. ``gens`` finding ``bogens`` —
    an infix LIKE pass over surface forms + lemma supplements FTS hits.
    """
    tokens = _tokenize_query(normalized_query)
    if not tokens:
        return []

    over_fetch = max(limit * 4, limit)
    use_contains = len(normalized_query) >= _PREFIX_MIN_LENGTH
    params = {
        "fts_query": _build_fts_query(tokens),
        "exact_query": normalized_query,
        "prefix_pattern": f"{normalized_query}%",
        # Sentinel that never matches when contains is disabled for short queries.
        "contains_pattern": f"%{normalized_query}%" if use_contains else "\x00",
        "owner_user_id": owner_user_id,
        "limit": over_fetch,
    }

    fts_rows = conn.execute(_SEARCH_SQL_FTS, params).fetchall()
    like_rows = conn.execute(_SEARCH_SQL_INFIX, params).fetchall()

    by_key: dict[tuple[int, int | None], dict] = {}
    for row in fts_rows:
        matched_via = _attribute_matched_via(row, normalized_query, tokens)
        key = (int(row["lexeme_id"]), row["meaning_id"])
        priority = _PRIORITY.get(matched_via, len(_PRIORITY)) if matched_via else len(_PRIORITY)
        by_key[key] = {
            "sort_key": (
                priority,
                row["fts_rank"] if row["fts_rank"] is not None else 0.0,
                (row["lemma"] or "").lower(),
            ),
            "payload": _row_to_dict(row, matched_via),
        }
    for row in like_rows:
        key = (int(row["lexeme_id"]), row["meaning_id"])
        if key in by_key:
            continue
        matched_via_infix = _attribute_matched_via_infix(row, normalized_query)
        by_key[key] = {
            "sort_key": (
                _PRIORITY.get(matched_via_infix, len(_PRIORITY)),
                0.0,
                (row["lemma"] or "").lower(),
            ),
            "payload": _row_to_dict(row, matched_via_infix),
        }

    enriched = sorted(by_key.values(), key=lambda item: item["sort_key"])
    # _FakeRow duck-types sqlite3.Row's __getitem__/keys interface that callers use.
    return [_FakeRow(item["payload"]) for item in enriched[:limit]]  # type: ignore[misc]


def _tokenize_query(query: str) -> list[str]:
    stripped = _strip_articles(query)
    cleaned: list[str] = []
    for token in _TOKEN_SPLIT.split(stripped):
        token = _WORD_CHAR_RE.sub("", token).strip()
        if token:
            cleaned.append(token)
    return cleaned


def _strip_articles(value: str) -> str:
    lowered = value.strip().lower()
    for prefix in (*_ENGLISH_ARTICLE_PREFIXES, *_DANISH_ARTICLE_PREFIXES):
        if lowered.startswith(prefix) and len(lowered) > len(prefix):
            return lowered[len(prefix):]
    return lowered


def _build_fts_query(tokens: list[str]) -> str:
    quoted = [f'"{token.replace(chr(34), "")}"' for token in tokens]
    if len(tokens) == 1 and len(tokens[0]) >= _PREFIX_MIN_LENGTH:
        return f"{quoted[0]} OR {tokens[0]}*"
    return " AND ".join(quoted)


_PRIORITY = {
    "lemma": 0,
    "surface": 1,
    "english_translation": 2,
    "alternative_translation": 3,
    "english_gloss": 4,
    "gloss": 5,
}


def _attribute_matched_via(
    row: sqlite3.Row, raw_query: str, tokens: list[str]
) -> str | None:
    query_low = raw_query.strip().lower()
    query_stripped = _strip_articles(raw_query)

    lemma = (row["lemma"] or "").lower()
    if lemma == query_low or lemma == query_stripped:
        return "lemma"

    surface_blob = (row["fts_surface_forms"] or "").lower()
    if _contains_any_form(surface_blob, [query_low, query_stripped]):
        return "surface"

    english_translation = (row["fts_english_translation"] or "").lower()
    et_stripped = _strip_articles(english_translation)
    if (
        english_translation == query_low
        or et_stripped == query_stripped
        or _token_appears_stemmed(f" {et_stripped} ", query_stripped)
    ):
        return "english_translation"

    alt_blob = (row["fts_alt_translations"] or "").lower()
    if _contains_whole_token_phrase(alt_blob, query_stripped, tokens):
        return "alternative_translation"

    english_gloss = (row["fts_english_gloss"] or "").lower()
    if _contains_whole_token_phrase(english_gloss, query_stripped, tokens):
        return "english_gloss"

    if english_translation.startswith(query_stripped) or query_stripped in english_translation:
        return "english_translation"

    gloss = (row["fts_gloss"] or "").lower()
    if _contains_whole_token_phrase(gloss, query_stripped, tokens):
        return "gloss"

    # FTS matched via prefix (e.g. "bog*" hit "bogstav") but no field above
    # took it — fall back to surface/lemma prefix-substring attribution.
    if surface_blob and any(token in surface_blob for token in tokens):
        return "surface"
    if any(token in lemma for token in tokens):
        return "lemma"

    return None


def _attribute_matched_via_infix(row: sqlite3.Row, raw_query: str) -> str:
    query_low = raw_query.strip().lower()
    lemma = (row["lemma"] or "").lower()
    if lemma == query_low:
        return "lemma"
    if row["match_surface"]:
        return "surface"
    if query_low and query_low in lemma:
        return "lemma"
    return "surface"


def _contains_any_form(blob: str, forms: Iterable[str]) -> bool:
    if not blob:
        return False
    padded = f" {blob} "
    return any(form and f" {form} " in padded for form in forms)


def _contains_whole_token_phrase(blob: str, phrase: str, tokens: list[str]) -> bool:
    if not blob or not phrase:
        return False
    padded = f" {blob} "
    if f" {phrase} " in padded:
        return True
    if all(_token_appears_stemmed(padded, token) for token in tokens):
        return True
    return False


def _token_appears_stemmed(padded_blob: str, token: str) -> bool:
    """Whole-word match that tolerates light English inflection on either side.

    "learns" hits "learn", "studied" hits "study", "buses" hits "bus".
    """
    if f" {token} " in padded_blob:
        return True
    for stem in _candidate_stems(token):
        if f" {stem} " in padded_blob:
            return True
        for blob_suffix in _ENGLISH_SUFFIXES:
            if f" {stem}{blob_suffix} " in padded_blob:
                return True
        if stem.endswith("i") and f" {stem[:-1]}y " in padded_blob:
            return True
    for blob_suffix in _ENGLISH_SUFFIXES:
        if f" {token}{blob_suffix} " in padded_blob:
            return True
    return False


def _candidate_stems(token: str) -> list[str]:
    stems: list[str] = []
    for suffix in _ENGLISH_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 1:
            stems.append(token[: -len(suffix)])
    # ied → y (studied → study, tried → try)
    if token.endswith("ied") and len(token) > 4:
        stems.append(token[:-3] + "y")
    return stems


def _row_to_dict(row: sqlite3.Row, matched_via: str | None) -> dict:
    return {
        "lemma": row["lemma"],
        "meaning_id": row["meaning_id"],
        "meaning_key": row["meaning_key"],
        "gloss": row["gloss"],
        "english_gloss": row["english_gloss"],
        "cor_lemma_idx": row["cor_lemma_idx"],
        "english_translation": row["english_translation"],
        "pos_tag": row["pos_tag"],
        "morphology": row["morphology"],
        "variation_count": row["variation_count"],
        "match_surface": row["match_surface"],
        "query_cor_ids": row["query_cor_ids"],
        "matched_via": matched_via,
    }


class _FakeRow:
    """Adapts a dict to the subset of sqlite3.Row used by callers."""

    __slots__ = ("_data",)

    def __init__(self, data: dict) -> None:
        self._data = data

    def __getitem__(self, key: str):
        return self._data[key]

    def keys(self):  # noqa: D401 — match sqlite3.Row protocol
        return self._data.keys()


_PROJECTION = """
        l.lemma,
        l.id AS lexeme_id,
        lm.id AS meaning_id,
        lm.meaning_key,
        lm.gloss,
        lm.english_gloss,
        lm.cor_lemma_idx,
        COALESCE(lm.english_translation, l.english_translation) AS english_translation,
        COALESCE(lm.pos_tag, l.pos_tag) AS pos_tag,
        COALESCE(lm.morphology, l.morphology) AS morphology,
        (
            SELECT COUNT(DISTINCT sf.form)
            FROM surface_forms sf
            WHERE (lm.id IS NOT NULL AND sf.meaning_id = lm.id)
               OR (lm.id IS NULL AND sf.lexeme_id = l.id AND sf.meaning_id IS NULL)
        ) AS variation_count,
        (
            SELECT sf.form
            FROM surface_forms sf
            WHERE (
                  (lm.id IS NOT NULL AND sf.meaning_id = lm.id)
               OR (lm.id IS NULL AND sf.lexeme_id = l.id AND sf.meaning_id IS NULL)
            )
              AND (
                  sf.form = :exact_query COLLATE NOCASE
               OR sf.form LIKE :prefix_pattern COLLATE NOCASE
               OR sf.form LIKE :contains_pattern COLLATE NOCASE
              )
            ORDER BY
                CASE
                    WHEN sf.form = :exact_query COLLATE NOCASE THEN 0
                    WHEN sf.form LIKE :prefix_pattern COLLATE NOCASE THEN 1
                    ELSE 2
                END,
                sf.form COLLATE NOCASE,
                sf.id ASC
            LIMIT 1
        ) AS match_surface,
        COALESCE((
            SELECT GROUP_CONCAT(sfcv.cor_id, char(31))
            FROM surface_forms sf
            JOIN surface_form_cor_variants sfcv ON sfcv.surface_form_id = sf.id
            WHERE (
                  (lm.id IS NOT NULL AND sf.meaning_id = lm.id)
               OR (lm.id IS NULL AND sf.lexeme_id = l.id AND sf.meaning_id IS NULL)
            )
              AND sf.form = :exact_query COLLATE NOCASE
        ), '') AS query_cor_ids
"""


_SEARCH_SQL_FTS = f"""
    WITH match_rows AS (
        SELECT
            fts.lexeme_id,
            fts.meaning_id,
            fts.gloss AS fts_gloss,
            fts.english_translation AS fts_english_translation,
            fts.english_gloss AS fts_english_gloss,
            fts.alt_translations AS fts_alt_translations,
            fts.surface_forms AS fts_surface_forms,
            bm25(wordbank_fts) AS fts_rank
        FROM wordbank_fts AS fts
        WHERE wordbank_fts MATCH :fts_query
          AND fts.owner_user_id = :owner_user_id
    )
    SELECT
        {_PROJECTION},
        mr.fts_english_translation,
        mr.fts_english_gloss,
        mr.fts_alt_translations,
        mr.fts_surface_forms,
        mr.fts_gloss,
        mr.fts_rank
    FROM match_rows mr
    JOIN lexemes l ON l.id = mr.lexeme_id
    LEFT JOIN lexeme_meanings lm ON lm.id = mr.meaning_id
    ORDER BY mr.fts_rank, l.lemma COLLATE NOCASE
    LIMIT :limit
"""


_SEARCH_SQL_INFIX = f"""
    WITH match_rows AS (
        -- Lemma infix hits
        SELECT l.id AS lexeme_id, lm.id AS meaning_id
        FROM lexemes l
        LEFT JOIN lexeme_meanings lm ON lm.lexeme_id = l.id
        WHERE l.owner_user_id = :owner_user_id
          AND (l.lemma = :exact_query COLLATE NOCASE
               OR l.lemma LIKE :prefix_pattern COLLATE NOCASE
               OR l.lemma LIKE :contains_pattern COLLATE NOCASE)

        UNION

        -- Meaning-scoped surface infix hits
        SELECT sf.lexeme_id, sf.meaning_id
        FROM surface_forms sf
        JOIN lexemes l ON l.id = sf.lexeme_id
        WHERE l.owner_user_id = :owner_user_id
          AND sf.meaning_id IS NOT NULL
          AND (sf.form = :exact_query COLLATE NOCASE
               OR sf.form LIKE :prefix_pattern COLLATE NOCASE
               OR sf.form LIKE :contains_pattern COLLATE NOCASE)

        UNION

        -- Lexeme-level (verb-style) surface infix hits
        SELECT sf.lexeme_id, NULL AS meaning_id
        FROM surface_forms sf
        JOIN lexemes l ON l.id = sf.lexeme_id
        WHERE l.owner_user_id = :owner_user_id
          AND sf.meaning_id IS NULL
          AND NOT EXISTS (
              SELECT 1 FROM lexeme_meanings lm2 WHERE lm2.lexeme_id = l.id
          )
          AND (sf.form = :exact_query COLLATE NOCASE
               OR sf.form LIKE :prefix_pattern COLLATE NOCASE
               OR sf.form LIKE :contains_pattern COLLATE NOCASE)
    )
    SELECT
        {_PROJECTION}
    FROM match_rows mr
    JOIN lexemes l ON l.id = mr.lexeme_id
    LEFT JOIN lexeme_meanings lm ON lm.id = mr.meaning_id
    ORDER BY
        CASE
            WHEN l.lemma = :exact_query COLLATE NOCASE THEN 0
            WHEN l.lemma LIKE :prefix_pattern COLLATE NOCASE THEN 1
            ELSE 2
        END,
        l.lemma COLLATE NOCASE,
        COALESCE(lm.id, 0)
    LIMIT :limit
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sqlite3


_POS_TO_UD = {
    "noun": "NOUN",
    "verb": "VERB",
    "adj": "ADJ",
    "adjective": "ADJ",
    "adv": "ADV",
    "adverb": "ADV",
    "name": "PROPN",
    "prop": "PROPN",
    "proper noun": "PROPN",
    "intj": "INTJ",
    "interjection": "INTJ",
    "conj": "CCONJ",
    "conjunction": "CCONJ",
    "prep": "ADP",
    "preposition": "ADP",
    "pron": "PRON",
    "pronoun": "PRON",
    "num": "NUM",
    "numeral": "NUM",
    "number": "NUM",
    "det": "DET",
    "determiner": "DET",
    "article": "DET",
    "particle": "PART",
    "prefix": "X",
    "suffix": "X",
    "abbrev": "X",
    "phrase": "X",
}


@dataclass(frozen=True)
class ENImportStats:
    total_rows: int
    inserted_entries: int
    inserted_forms: int
    skipped_rows: int
    skipped_multiword: int
    skipped_non_english: int
    skipped_empty: int


def _pos_to_ud(pos_raw: str) -> str:
    return _POS_TO_UD.get(pos_raw.strip().lower(), "X")


def _pick_ipa(sounds) -> str | None:
    if not isinstance(sounds, list):
        return None
    for entry in sounds:
        if isinstance(entry, dict) and isinstance(entry.get("ipa"), str):
            return entry["ipa"].strip() or None
    return None


def _extract_glosses(senses) -> list[tuple[str, list[str]]]:
    """Return list of (gloss, examples) per sense."""
    out: list[tuple[str, list[str]]] = []
    if not isinstance(senses, list):
        return out
    for sense in senses:
        if not isinstance(sense, dict):
            continue
        glosses = sense.get("glosses")
        if not isinstance(glosses, list) or not glosses:
            continue
        gloss = next((str(g).strip() for g in glosses if isinstance(g, str) and g.strip()), "")
        if not gloss:
            continue
        examples_raw = sense.get("examples") if isinstance(sense.get("examples"), list) else []
        examples: list[str] = []
        for ex in examples_raw:
            if isinstance(ex, dict):
                text = ex.get("text")
                if isinstance(text, str) and text.strip():
                    examples.append(text.strip())
        out.append((gloss, examples))
    return out


def _extract_forms(forms) -> list[tuple[str, list[str]]]:
    """Return list of (form_surface, tags) excluding the headword itself (handled separately)."""
    out: list[tuple[str, list[str]]] = []
    if not isinstance(forms, list):
        return out
    for form in forms:
        if not isinstance(form, dict):
            continue
        surface = form.get("form")
        if not isinstance(surface, str):
            continue
        surface = surface.strip()
        if not surface or " " in surface:
            continue
        tags = form.get("tags")
        if not isinstance(tags, list):
            tags = []
        tags = [str(t) for t in tags if isinstance(t, str)]
        if "canonical" in tags:
            # Wiktionary flags the page's true lemma with "canonical"; the entry
            # `word` is then a metadata title, not an inflection. Skip — the base
            # form has its own entry elsewhere.
            continue
        out.append((surface, tags))
    return out


def build_english_sqlite(
    *,
    input_path: Path,
    output_path: Path,
    batch_size: int = 10_000,
) -> ENImportStats:
    if batch_size < 1:
        raise ValueError("batch_size must be >= 1")
    if not input_path.exists():
        raise FileNotFoundError(f"Input JSONL not found at {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        output_path.unlink()

    conn = sqlite3.connect(output_path)
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA temp_store = MEMORY")
        _create_schema(conn)

        total_rows = 0
        inserted_entries = 0
        inserted_forms = 0
        skipped_rows = 0
        skipped_multiword = 0
        skipped_non_english = 0
        skipped_empty = 0

        entry_batch: list[tuple[object, ...]] = []
        form_batch: list[tuple[object, ...]] = []
        seen_forms: set[tuple[str, str, str]] = set()

        with input_path.open("r", encoding="utf-8") as handle:
            for raw_line in handle:
                total_rows += 1
                line = raw_line.strip()
                if not line:
                    skipped_rows += 1
                    skipped_empty += 1
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    skipped_rows += 1
                    continue

                lang_code = row.get("lang_code")
                if lang_code != "en":
                    skipped_rows += 1
                    skipped_non_english += 1
                    continue

                word = row.get("word")
                if not isinstance(word, str) or not word.strip():
                    skipped_rows += 1
                    skipped_empty += 1
                    continue
                word = word.strip()
                if " " in word:
                    skipped_rows += 1
                    skipped_multiword += 1
                    continue

                pos_raw = row.get("pos")
                if not isinstance(pos_raw, str) or not pos_raw.strip():
                    skipped_rows += 1
                    skipped_empty += 1
                    continue
                pos_ud = _pos_to_ud(pos_raw)

                glosses = _extract_glosses(row.get("senses"))
                if not glosses:
                    skipped_rows += 1
                    skipped_empty += 1
                    continue

                ipa = _pick_ipa(row.get("sounds"))
                lemma = word
                lemma_lower = lemma.lower()

                for sense_idx, (gloss, examples) in enumerate(glosses):
                    en_id = f"EN.{lemma_lower}.{pos_ud}.{sense_idx:02d}"
                    entry_batch.append(
                        (
                            en_id,
                            lemma,
                            lemma_lower,
                            pos_raw.strip().lower(),
                            pos_ud,
                            sense_idx,
                            gloss,
                            json.dumps(examples, ensure_ascii=False),
                            ipa,
                        )
                    )
                    inserted_entries += 1

                headword_key = (lemma_lower, lemma_lower, pos_ud)
                if headword_key not in seen_forms:
                    seen_forms.add(headword_key)
                    form_batch.append((lemma, lemma_lower, lemma, pos_ud, json.dumps([], ensure_ascii=False)))
                    inserted_forms += 1

                for surface, tags in _extract_forms(row.get("forms")):
                    form_key = (surface.lower(), lemma_lower, pos_ud)
                    if form_key in seen_forms:
                        continue
                    seen_forms.add(form_key)
                    form_batch.append(
                        (surface, surface.lower(), lemma, pos_ud, json.dumps(tags, ensure_ascii=False))
                    )
                    inserted_forms += 1

                if len(entry_batch) >= batch_size:
                    _insert_entries(conn, entry_batch)
                    entry_batch.clear()
                if len(form_batch) >= batch_size:
                    _insert_forms(conn, form_batch)
                    form_batch.clear()

        if entry_batch:
            _insert_entries(conn, entry_batch)
            entry_batch.clear()
        if form_batch:
            _insert_forms(conn, form_batch)
            form_batch.clear()

        _create_indexes(conn)
        conn.commit()
        return ENImportStats(
            total_rows=total_rows,
            inserted_entries=inserted_entries,
            inserted_forms=inserted_forms,
            skipped_rows=skipped_rows,
            skipped_multiword=skipped_multiword,
            skipped_non_english=skipped_non_english,
            skipped_empty=skipped_empty,
        )
    finally:
        conn.close()


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE en_entries (
            en_id TEXT PRIMARY KEY,
            lemma TEXT NOT NULL,
            lemma_lower TEXT NOT NULL,
            pos_raw TEXT NOT NULL,
            pos_ud TEXT NOT NULL,
            sense_idx INTEGER NOT NULL,
            gloss TEXT NOT NULL,
            examples_json TEXT NOT NULL,
            ipa TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE en_forms (
            form TEXT NOT NULL,
            form_lower TEXT NOT NULL,
            lemma TEXT NOT NULL,
            pos_ud TEXT NOT NULL,
            tags_json TEXT NOT NULL,
            PRIMARY KEY (form_lower, lemma, pos_ud)
        )
        """
    )


def _insert_entries(conn: sqlite3.Connection, batch: list[tuple[object, ...]]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO en_entries (
            en_id, lemma, lemma_lower, pos_raw, pos_ud, sense_idx, gloss, examples_json, ipa
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        batch,
    )


def _insert_forms(conn: sqlite3.Connection, batch: list[tuple[object, ...]]) -> None:
    conn.executemany(
        """
        INSERT OR IGNORE INTO en_forms (
            form, form_lower, lemma, pos_ud, tags_json
        ) VALUES (?, ?, ?, ?, ?)
        """,
        batch,
    )


def _create_indexes(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE INDEX idx_en_entries_lemma_lower ON en_entries(lemma_lower)")
    conn.execute("CREATE INDEX idx_en_entries_lemma_pos ON en_entries(lemma_lower, pos_ud)")
    conn.execute("CREATE INDEX idx_en_forms_form_lower ON en_forms(form_lower)")
    conn.execute("CREATE INDEX idx_en_forms_lemma ON en_forms(lemma)")

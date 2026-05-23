"""Multi-word expression (MWE / phrasal verb) helpers used by the sentence-save flow.

This module owns the MWE-specific slice of token resolution:
- `MWEToken` — the merged-token type produced from Gemini's mwe_spans
- `align_tokens_to_source` + `merge_mwe_spans` — coalesce Gemini spans against the
  NLP-tokenized sentence, extracting intervening fillers like "ikke" / "selv om"
- `_ensure_mwe_meaning_section` — upsert a lexeme_meanings row + link orphan surface
  forms + queue meaning-level verification
- `_upsert_mwe_surface_form_preserving_meaning` — write the encountered surface form
  without creating a duplicate orphan row on re-save
- `_infer_mwe_surface_morphology` — derive morphology for the surface from the head
  verb's COR entry so the form slots into the right paradigm row (e.g. Imperative)

Lives in `services/use_cases/` so it can call into both the wordbank runtime and
the sentence-verification result types without crossing layer boundaries.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass

from app.nlp.adapter import NLPToken
from app.services.sentence_verification import SentenceMWESpan
from app.services.token_classifier import normalize_token
from app.services.use_cases.wordbank.runtime import WordbankRuntime

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MWEToken(NLPToken):
    pos_tag: str | None = None
    gloss: str | None = None
    english_translation: str | None = None


def align_tokens_to_source(
    sentence_tokens: list[NLPToken],
    source_text: str,
) -> list[tuple[NLPToken, int, int]]:
    aligned: list[tuple[NLPToken, int, int]] = []
    current_idx = 0
    for token in sentence_tokens:
        pos = source_text.find(token.text, current_idx)
        if pos == -1:
            pos = source_text.find(token.text, 0)
        if pos != -1:
            start = pos
            end = pos + len(token.text)
            aligned.append((token, start, end))
            current_idx = end
        else:
            aligned.append((token, current_idx, current_idx + len(token.text)))
            current_idx += len(token.text)
    return aligned


# Words commonly inserted between the verb and its particle in split phrasal verbs.
# These get extracted from the merged MWE token and emitted as their own NLP tokens.
_MWE_FILLER_WORDS = frozenset(
    {
        "ikke", "aldrig", "måske", "vist", "sgu", "da", "jo", "nok", "vel",
        "kun", "og", "eller", "men", "selv", "om",
    }
)


def merge_mwe_spans(
    sentence_tokens: list[NLPToken],
    source_text: str,
    mwe_spans: list[SentenceMWESpan] | None,
    runtime: WordbankRuntime | None = None,
) -> list[NLPToken]:
    if not mwe_spans:
        return sentence_tokens

    aligned = align_tokens_to_source(sentence_tokens, source_text)

    # Drop spans whose lemma is empty or single-word — Gemini occasionally over-reports
    # (e.g. tagging a single verb as an MWE). Merging those produces a 1-token "MWE"
    # which is just the original token with confusing extra metadata.
    filtered_spans = [
        span for span in mwe_spans
        if normalize_token(span.lemma) and len(span.lemma.split()) >= 2
    ]
    if not filtered_spans:
        return sentence_tokens

    # Coalesce close spans pointing to the same normalized lemma and pos_tag.
    coalesced_spans: list[SentenceMWESpan] = []
    spans_sorted = sorted(filtered_spans, key=lambda s: s.start)
    for span in spans_sorted:
        merged = False
        norm_lemma = normalize_token(span.lemma)
        norm_pos = (span.pos_tag or "").upper()
        for i, existing in enumerate(coalesced_spans):
            exist_lemma = normalize_token(existing.lemma)
            exist_pos = (existing.pos_tag or "").upper()
            if exist_lemma == norm_lemma and exist_pos == norm_pos:
                dist = span.start - existing.end
                if 0 <= dist <= 40:
                    coalesced_spans[i] = SentenceMWESpan(
                        start=min(existing.start, span.start),
                        end=max(existing.end, span.end),
                        surface=source_text[
                            min(existing.start, span.start):max(existing.end, span.end)
                        ],
                        lemma=existing.lemma,
                        pos_tag=existing.pos_tag,
                        gloss=existing.gloss or span.gloss,
                        english_translation=existing.english_translation or span.english_translation,
                    )
                    merged = True
                    break
        if not merged:
            coalesced_spans.append(span)

    sorted_spans = sorted(coalesced_spans, key=lambda s: s.start, reverse=True)

    for span in sorted_spans:
        overlapping_indices = [
            idx for idx, (_token, start, end) in enumerate(aligned)
            if max(start, span.start) < min(end, span.end)
        ]
        if not overlapping_indices:
            continue

        lemma_words = {normalize_token(w) for w in span.lemma.split() if w}
        constituent_indices: list[int] = []
        extra_indices: list[int] = []

        for idx in overlapping_indices:
            token, _start, _end = aligned[idx]
            candidate_lemmas = {normalize_token(token.lemma), normalize_token(token.text)}
            if runtime is not None and getattr(runtime, "cor", None) is not None:
                try:
                    entries = runtime.cor.lookup_form(token.text)
                    for entry in entries:
                        candidate_lemmas.add(normalize_token(entry.lemma))
                except (FileNotFoundError, sqlite3.OperationalError) as exc:
                    logger.warning(
                        "mwe_constituent_cor_lookup_failed",
                        extra={"token_text": token.text, "error": str(exc)},
                    )

            is_constituent = any(lem in lemma_words for lem in candidate_lemmas if lem)
            if not is_constituent:
                tok_text_norm = normalize_token(token.text)
                if tok_text_norm not in _MWE_FILLER_WORDS and not token.is_punctuation:
                    is_constituent = True

            (constituent_indices if is_constituent else extra_indices).append(idx)

        if not constituent_indices:
            continue

        constituent_tokens_sorted = sorted(
            (aligned[i] for i in constituent_indices), key=lambda x: x[1]
        )
        extra_tokens_sorted = sorted(
            (aligned[i] for i in extra_indices), key=lambda x: x[1]
        )
        merged_surface = " ".join(t[0].text for t in constituent_tokens_sorted)
        mwe_pos = span.pos_tag or "VERB"
        mwe_token = MWEToken(
            text=merged_surface,
            lemma=span.lemma,
            pos=mwe_pos,
            morphology=None,
            is_punctuation=False,
            pos_tag=mwe_pos,
            gloss=span.gloss,
            english_translation=span.english_translation,
        )

        first_idx = overlapping_indices[0]
        last_idx = overlapping_indices[-1]
        replacement = [(mwe_token, span.start, span.end)]
        for extra_tok, ext_start, ext_end in extra_tokens_sorted:
            replacement.append((extra_tok, ext_start, ext_end))
        aligned[first_idx : last_idx + 1] = replacement

    return [t[0] for t in aligned]


def ensure_mwe_meaning_section(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    pos_tag: str | None,
    gloss: str | None,
    english_translation: str | None,
    cor_entry: object | None = None,
) -> None:
    """Create (or update) a `lexeme_meanings` row for an MWE lemma and link orphan surface forms.

    Also queues word-page verification — must run AFTER the meaning exists so the
    discovery walk picks up meaning-level targets in a single pass.
    """
    from app.services.use_cases.wordbank.verification_targets import (
        discover_word_page_verification_targets,
        queue_verification_targets,
    )

    lexeme = runtime.repository.get_lexeme(lemma)
    if lexeme is None:
        return
    dictionary_status = "cor" if cor_entry is not None else "generated_non_cor"
    cor_lemma_idx = getattr(cor_entry, "lemma_idx", None) if cor_entry is not None else None
    try:
        meaning_record, _inserted = runtime.repository.upsert_lexeme_meaning(
            lexeme_id=lexeme.id,
            meaning_key=normalize_token(lemma) or lemma,
            cor_lemma_idx=cor_lemma_idx,
            dictionary_status=dictionary_status,
            gloss=gloss,
            english_translation=english_translation,
            pos_tag=pos_tag,
            morphology=None,
        )
    except LookupError:
        logger.warning("mwe_meaning_upsert_lexeme_missing", extra={"lemma": lemma})
        return
    runtime.repository.assign_orphan_surface_forms_to_meaning(
        lexeme_id=lexeme.id,
        meaning_id=meaning_record.id,
    )
    queue_verification_targets(
        runtime,
        stored_lemma=lemma,
        targets=discover_word_page_verification_targets(runtime, stored_lemma=lemma),
    )


def upsert_mwe_surface_form_preserving_meaning(
    runtime: WordbankRuntime,
    *,
    lemma: str,
    form: str,
    pos_tag: str,
    morphology: str,
) -> None:
    """Upsert an MWE surface form without creating an orphan duplicate on re-save.

    `insert_or_update_surface_form` keys on `(lexeme_id, meaning_id, form)`. Passing
    `meaning_id=None` when the surface form already lives under a specific meaning
    inserts a new orphan row that `ensure_mwe_meaning_section` then has to heal.
    Look up the existing meaning_id first and pass it through so the existing row
    is updated in place.
    """
    lexeme = runtime.repository.get_lexeme(lemma)
    if lexeme is None:
        return
    existing_rows = runtime.repository.find_surface_forms(lexeme_id=lexeme.id, form=form)
    target_meaning_id: int | None = None
    for row in existing_rows:
        if row.meaning_id is not None:
            target_meaning_id = row.meaning_id
            break
    runtime.repository.insert_or_update_surface_form(
        lexeme_id=lexeme.id,
        meaning_id=target_meaning_id,
        form=form,
        pos_tag=pos_tag,
        morphology=morphology,
        source="search",
    )


def infer_mwe_surface_morphology(
    runtime: WordbankRuntime,
    *,
    surface: str,
    lemma: str,
    pos_tag: str | None,
) -> str | None:
    """Infer the morphology of an MWE surface form from its head verb's COR entry.

    For `pas på` (lemma `passe på`), looks up `pas` in COR and returns the matching
    verb form's morphology (`Mood=Imp|VerbForm=Fin`). Enables the surface to slot
    into the right paradigm row instead of falling into "Other forms".
    """
    if (pos_tag or "").upper() != "VERB":
        return None
    surface_parts = [part for part in surface.split() if part]
    lemma_parts = [part for part in lemma.split() if part]
    # Must be multi-word both sides for paradigm-particle inference to make sense.
    if len(surface_parts) < 2 or len(lemma_parts) < 2:
        return None
    head_surface = surface_parts[0]
    head_lemma = lemma_parts[0]
    if not head_surface or not head_lemma:
        return None
    try:
        entries = runtime.cor.lookup_form(head_surface)
    except (FileNotFoundError, sqlite3.OperationalError) as exc:
        logger.warning(
            "mwe_head_cor_lookup_failed",
            extra={"head_surface": head_surface, "error": str(exc)},
        )
        return None
    for entry in entries:
        if entry.pos_tag != "VERB" or entry.norm != "N":
            continue
        if normalize_token(entry.lemma) != head_lemma:
            continue
        if entry.morphology:
            return entry.morphology
    return None

from __future__ import annotations

from typing import Literal

from app.api.schemas.v1.sentencebank import (
    AddSentenceResponse,
    QueuedSentencePronunciationTask,
    SentenceSummary,
    SentenceTokenCard,
)
from app.db.repositories.sentencebank import SentenceRecord


def sentence_token_card(token) -> SentenceTokenCard:
    return SentenceTokenCard(
        token_index=token.token_index,
        surface_form=token.surface_form,
        save_status=getattr(token, "save_status", "saved") or "saved",
        lemma_candidate=getattr(token, "lemma_candidate", None),
        stored_lemma=token.stored_lemma,
        lexeme_id=token.lexeme_id,
        meaning_id=token.meaning_id,
        pos_tag=token.pos_tag,
        morphology=token.morphology,
        gloss=token.gloss,
        english_translation=token.english_translation,
        gloss_translation=token.gloss_translation,
    )


def sentence_summary(row: SentenceRecord) -> SentenceSummary:
    return SentenceSummary(
        id=row.id,
        source_text=row.source_text,
        english_translation=row.english_translation,
        created_at=row.created_at,
        has_pronunciation=row.has_pronunciation,
        tokens=[sentence_token_card(token) for token in row.tokens],
    )


def sentence_response(
    row: SentenceRecord,
    *,
    status: Literal["inserted", "exists"],
    message: str,
    pronunciation: QueuedSentencePronunciationTask | None = None,
) -> AddSentenceResponse:
    return AddSentenceResponse(
        id=row.id,
        source_text=row.source_text,
        english_translation=row.english_translation,
        created_at=row.created_at,
        has_pronunciation=row.has_pronunciation,
        tokens=[sentence_token_card(token) for token in row.tokens],
        status=status,
        message=message,
        pronunciation=pronunciation,
    )

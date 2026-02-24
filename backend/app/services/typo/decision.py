from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.typo.ranking import RankedCandidate


TypoClassification = Literal["typo_likely", "uncertain", "new"]


@dataclass(frozen=True)
class DecisionResult:
    status: TypoClassification
    confidence: float
    reason_tags: tuple[str, ...]


def decide_status(
    *,
    ranked: list[RankedCandidate],
    proper_noun_bias: bool = False,
    typo_threshold: float = 0.84,
    uncertain_threshold: float = 0.56,
    min_margin: float = 0.12,
) -> DecisionResult:
    if not ranked:
        return DecisionResult(status="new", confidence=0.0, reason_tags=("weak_candidate_evidence",))

    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    margin = top.score - second.score if second else top.score

    if proper_noun_bias:
        if top.score >= uncertain_threshold:
            return DecisionResult(
                status="uncertain",
                confidence=top.score,
                reason_tags=("proper_noun_bias", "candidate_medium_confidence"),
            )
        return DecisionResult(status="new", confidence=top.score, reason_tags=("proper_noun_bias",))

    if top.score >= typo_threshold and margin >= min_margin:
        return DecisionResult(
            status="typo_likely",
            confidence=top.score,
            reason_tags=("candidate_high_confidence", "clear_margin"),
        )
    if top.score >= uncertain_threshold:
        tags = ("candidate_medium_confidence",)
        if margin < min_margin:
            tags += ("small_margin",)
        return DecisionResult(status="uncertain", confidence=top.score, reason_tags=tags)
    return DecisionResult(status="new", confidence=top.score, reason_tags=("weak_candidate_evidence",))

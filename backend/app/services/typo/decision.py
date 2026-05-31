from __future__ import annotations

from dataclasses import dataclass
import math
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

    # Keep primary decision signal close to pre-regression behavior (raw ranking score + margin),
    # and use posterior only as a secondary stabilizer.
    posterior_top2 = _top2_posterior(top.score, second.score if second else None)
    confidence = _blended_confidence(top.score, posterior_top2)

    margin = top.score - second.score if second else top.score
    calibrated_typo_threshold = _calibrate_threshold(typo_threshold, top.prior_score)
    calibrated_uncertain_threshold = _calibrate_threshold(uncertain_threshold, top.prior_score)

    if proper_noun_bias:
        if confidence >= calibrated_uncertain_threshold:
            return DecisionResult(
                status="uncertain",
                confidence=confidence,
                reason_tags=("proper_noun_bias", "candidate_medium_confidence"),
            )
        return DecisionResult(status="new", confidence=confidence, reason_tags=("proper_noun_bias",))

    if confidence >= calibrated_typo_threshold and margin >= min_margin:
        return DecisionResult(
            status="typo_likely",
            confidence=confidence,
            reason_tags=("candidate_high_confidence", "clear_margin", "posterior_calibrated"),
        )

    # Distance-1 and high error-likelihood candidates are frequently true typos in Danish fixtures.
    near_typo_cutoff = calibrated_typo_threshold - 0.04
    if (
        top.distance <= 1
        and top.error_likelihood >= 0.82
        and confidence >= near_typo_cutoff
        and margin >= (min_margin * 0.75)
    ):
        return DecisionResult(
            status="typo_likely",
            confidence=confidence,
            reason_tags=("candidate_high_confidence", "distance_one_boost", "posterior_calibrated"),
        )
    if confidence >= calibrated_uncertain_threshold:
        tags = ("candidate_medium_confidence", "posterior_calibrated")
        if margin < min_margin:
            tags += ("small_margin",)
        return DecisionResult(status="uncertain", confidence=confidence, reason_tags=tags)

    return DecisionResult(status="new", confidence=confidence, reason_tags=("weak_candidate_evidence",))


def _top2_posterior(top_score: float, second_score: float | None, *, temperature: float = 0.35) -> float:
    if second_score is None:
        return 1.0
    hi = max(top_score, second_score)
    a = math.exp((top_score - hi) / temperature)
    b = math.exp((second_score - hi) / temperature)
    total = a + b
    if total <= 0:
        return 0.0
    return a / total


def _blended_confidence(raw_score: float, posterior: float) -> float:
    # Anchor confidence on raw score (stable with existing thresholds),
    # while still adding posterior separation in close races.
    return max(0.0, min(1.0, (0.78 * raw_score) + (0.22 * posterior)))


def _calibrate_threshold(base: float, prior_score: float) -> float:
    # Mild prior-aware adjustment; avoid over-shifting decision boundaries.
    adjusted = base - ((prior_score - 0.5) * 0.02)
    return max(0.2, min(0.98, adjusted))

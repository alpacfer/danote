from __future__ import annotations

from app.services.typo.candidates import Candidate
from app.services.typo.decision import decide_status
from app.services.typo.ranking import rank_candidates


def test_rank_candidates_prefers_danish_diacritic_substitution() -> None:
    ranked = rank_candidates(
        token="borne",
        candidates=[
            Candidate(value="børne", distance=1, source_flags=("from_symspell",), frequency=10),
            Candidate(value="barne", distance=1, source_flags=("from_symspell",), frequency=10),
        ],
        known_lemmas=set(),
    )

    assert ranked[0].value == "børne"
    assert ranked[0].error_likelihood > ranked[1].error_likelihood


def test_decide_status_uses_posterior_calibration_tags() -> None:
    ranked = rank_candidates(
        token="spisr",
        candidates=[
            Candidate(value="spiser", distance=1, source_flags=("from_user_dict",), frequency=120),
            Candidate(value="spids", distance=2, source_flags=("from_symspell",), frequency=3),
        ],
        known_lemmas={"spiser"},
    )

    result = decide_status(
        ranked=ranked,
        proper_noun_bias=False,
        typo_threshold=0.55,
        uncertain_threshold=0.35,
        min_margin=0.05,
    )

    assert result.status == "typo_likely"
    assert "posterior_calibrated" in result.reason_tags
    assert 0.0 <= result.confidence <= 1.0


def test_decide_status_respects_proper_noun_bias() -> None:
    ranked = rank_candidates(
        token="Aarhuss",
        candidates=[
            Candidate(value="aarhus", distance=1, source_flags=("from_symspell",), frequency=30),
        ],
        known_lemmas=set(),
    )

    result = decide_status(
        ranked=ranked,
        proper_noun_bias=True,
        typo_threshold=0.5,
        uncertain_threshold=0.2,
        min_margin=0.02,
    )

    assert result.status in {"uncertain", "new"}
    assert "proper_noun_bias" in result.reason_tags


def test_decide_status_promotes_distance_one_high_likelihood_to_typo() -> None:
    ranked = rank_candidates(
        token="spisr",
        candidates=[
            Candidate(value="spiser", distance=1, source_flags=("from_symspell",), frequency=60),
            Candidate(value="spids", distance=2, source_flags=("from_symspell",), frequency=20),
        ],
        known_lemmas={"spiser"},
    )

    result = decide_status(
        ranked=ranked,
        proper_noun_bias=False,
        typo_threshold=0.79,
        uncertain_threshold=0.5,
        min_margin=0.1,
    )

    assert result.status == "typo_likely"
    assert "distance_one_boost" in result.reason_tags

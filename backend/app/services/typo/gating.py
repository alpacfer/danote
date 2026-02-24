from __future__ import annotations

import re
from dataclasses import dataclass


EMAIL_RE = re.compile(r"^\S+@\S+\.\S+$")
URL_RE = re.compile(r"^(https?://|www\.)\S+$", flags=re.IGNORECASE)
PATH_RE = re.compile(r"^([A-Za-z]:\\|/).+")


@dataclass(frozen=True)
class GatingResult:
    should_run: bool
    reason_tags: tuple[str, ...]
    proper_noun_bias: bool = False


def should_run_typo_check(
    *,
    token: str,
    normalized: str,
    min_len: int = 3,
    sentence_start: bool = False,
) -> GatingResult:
    if not normalized:
        return GatingResult(False, ("gating_skip_empty",))
    if len(normalized) < min_len:
        return GatingResult(False, ("gating_skip_short",))
    if EMAIL_RE.match(normalized):
        return GatingResult(False, ("gating_skip_email",))
    if URL_RE.match(normalized):
        return GatingResult(False, ("gating_skip_url",))
    if PATH_RE.match(normalized):
        return GatingResult(False, ("gating_skip_path",))
    if token.isupper() and any(char.isalpha() for char in token):
        return GatingResult(False, ("gating_skip_acronym",))

    digit_count = sum(char.isdigit() for char in normalized)
    alpha_count = sum(char.isalpha() for char in normalized)
    total = len(normalized)
    if total and digit_count / total > 0.3:
        return GatingResult(False, ("gating_skip_digit_ratio",))
    if alpha_count == 0:
        return GatingResult(False, ("gating_skip_non_alpha",))

    proper_noun_bias = (
        not sentence_start
        and token[:1].isupper()
        and any(char.isalpha() for char in token)
    )
    tags = ("gating_ok",)
    if proper_noun_bias:
        tags += ("proper_noun_bias",)
    return GatingResult(True, tags, proper_noun_bias=proper_noun_bias)

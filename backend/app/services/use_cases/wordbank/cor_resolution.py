from __future__ import annotations

from app.services.use_cases.wordbank.cor_resolution_actions import WordbankCorResolutionActionsMixin
from app.services.use_cases.wordbank.cor_resolution_local import WordbankCorResolutionLocalMixin
from app.services.use_cases.wordbank.cor_resolution_resolve import WordbankCorResolutionResolveMixin


class WordbankCorResolutionMixin(
    WordbankCorResolutionResolveMixin,
    WordbankCorResolutionActionsMixin,
    WordbankCorResolutionLocalMixin,
):
    pass

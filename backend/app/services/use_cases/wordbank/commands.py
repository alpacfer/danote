from __future__ import annotations

from app.services.use_cases.wordbank.commands_mutation import WordbankCommandsMutationMixin
from app.services.use_cases.wordbank.commands_pronunciation import WordbankCommandsPronunciationMixin
from app.services.use_cases.wordbank.commands_support import WordbankCommandsSupportMixin
from app.services.use_cases.wordbank.commands_verification_apply import WordbankCommandsVerificationApplyMixin


class WordbankCommandsMixin(
    WordbankCommandsMutationMixin,
    WordbankCommandsPronunciationMixin,
    WordbankCommandsVerificationApplyMixin,
    WordbankCommandsSupportMixin,
):
    pass

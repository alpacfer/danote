from __future__ import annotations

from app.services.use_cases.wordbank.collaborators.translation_word_frames import (
    WordTranslationFrame as CORAzureFrame,
    cleanup_framed_word_translation as azure_framed_translation_for_comparison,
    cor_entry_word_translation_frame as cor_entry_azure_frame,
    cor_local_word_translation_frame as cor_local_azure_frame,
)


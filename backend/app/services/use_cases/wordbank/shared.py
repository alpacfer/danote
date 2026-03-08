from __future__ import annotations

import io
import wave
from dataclasses import dataclass
from typing import Literal

from app.api.schemas.v1.wordbank import WordActionSuggestion
from app.services.tts import PronunciationAudio


def _looks_like_wav(payload: bytes) -> bool:
    return len(payload) >= 12 and payload[:4] == b"RIFF" and payload[8:12] == b"WAVE"


def _pcm_to_wav_bytes(pcm_data: bytes, *, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm_data)
    return buffer.getvalue()


def _is_pcm_like_mime(mime_type: str | None) -> bool:
    if not isinstance(mime_type, str):
        return False
    normalized = mime_type.strip().lower()
    return normalized.startswith("audio/pcm") or normalized.startswith("audio/l16") or "codec=pcm" in normalized


def _normalize_pronunciation_audio(audio: PronunciationAudio) -> PronunciationAudio:
    normalized_mime = audio.mime_type.strip().lower() if isinstance(audio.mime_type, str) else ""
    if _is_pcm_like_mime(normalized_mime):
        return PronunciationAudio(audio_bytes=_pcm_to_wav_bytes(audio.audio_bytes), mime_type="audio/wav")
    if _looks_like_wav(audio.audio_bytes):
        return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type="audio/wav")
    if normalized_mime:
        return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type=normalized_mime)
    return PronunciationAudio(audio_bytes=audio.audio_bytes, mime_type="audio/wav")


def _normalize_action_value(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _cor_entry_priority(entry: object, normalized_surface: str) -> tuple:
    """Scoring key for selecting the best COREntry from a list.

    Lower is better. Used by both NLPCollaborator and CorResolutionCollaborator.
    """
    norm_status = getattr(entry, "norm_status", None)
    if norm_status == "N":
        norm_rank = 0
    elif norm_status == "K":
        norm_rank = 1
    elif norm_status == "U":
        norm_rank = 2
    else:
        norm_rank = 3
    full_form = getattr(entry, "full_form", "") or ""
    lemma = getattr(entry, "lemma", "") or ""
    pos_tag = getattr(entry, "pos_tag", None)
    morphology = getattr(entry, "morphology", None)
    cor_id = getattr(entry, "cor_id", "")
    is_exact_surface = 0 if _normalize_action_value(full_form) == _normalize_action_value(normalized_surface) else 1
    lemma_matches_surface = 0 if _normalize_action_value(lemma) == _normalize_action_value(normalized_surface) else 1
    noun_number_rank = 2
    if pos_tag == "NOUN":
        morph_str = morphology or ""
        if "Number=Sing" in morph_str:
            noun_number_rank = 0
        elif "Number=Plur" in morph_str:
            noun_number_rank = 1
    has_pos = 0 if pos_tag else 1
    has_morph = 0 if morphology else 1
    return (is_exact_surface, norm_rank, lemma_matches_surface, noun_number_rank, has_pos, has_morph, lemma, cor_id)


@dataclass(frozen=True)
class _CORAddOption:
    surface: str
    lemma: str
    cor_id: str | None
    pos_tag: str | None
    morphology: str | None
    translation_label: str | None


def build_word_action_suggestions(
    *,
    classification: Literal["known", "variation", "typo_likely", "uncertain", "new"],
    query_surface: str,
    query_lemma: str | None,
    query_pos_tag: str | None,
    query_morphology: str | None,
    matched_lemma: str | None,
    da_to_en_translation: str | None,
    en_to_da_translation: str | None,
    en_to_da_lemma: str | None,
    en_to_da_pos_tag: str | None,
    en_to_da_morphology: str | None,
    query_language: Literal["en", "da", "ambiguous"] | None,
    query_language_confidence: float | None,
) -> list[WordActionSuggestion]:
    query_surface_clean = query_surface.strip()
    query_lemma_clean = query_lemma.strip() if query_lemma else ""
    actions: list[WordActionSuggestion] = []

    if classification == "known":
        known_lemma = matched_lemma or query_lemma_clean or query_surface_clean
        if known_lemma:
            actions.append(
                WordActionSuggestion(
                    action_type="open_wordbank",
                    surface=query_surface_clean,
                    lemma=known_lemma,
                    direction="known",
                    direction_label="Wordbank",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                )
            )
        return actions

    if classification == "variation" and matched_lemma:
        if _normalize_action_value(query_surface_clean) != _normalize_action_value(matched_lemma):
            actions.append(
                WordActionSuggestion(
                    action_type="add_variation",
                    surface=query_surface_clean,
                    lemma=matched_lemma,
                    translation_label=query_surface_clean,
                    direction="variation",
                    direction_label="Variation",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                )
            )
        return actions

    if classification == "typo_likely" and not da_to_en_translation and not en_to_da_translation:
        return []

    if query_surface_clean:
        lemma_value = query_lemma_clean or query_surface_clean
        if da_to_en_translation or not en_to_da_translation:
            actions.append(
                WordActionSuggestion(
                    action_type="add_as_new",
                    surface=query_surface_clean,
                    lemma=lemma_value,
                    translation_label=da_to_en_translation or query_surface_clean,
                    direction="da_to_en",
                    direction_label="Danish -> English",
                    pos_tag=query_pos_tag,
                    morphology=query_morphology,
                    show_lemma=_normalize_action_value(query_surface_clean) != _normalize_action_value(lemma_value),
                )
            )

    if en_to_da_translation and not (query_language == "da" and (query_language_confidence or 0) >= 0.7):
        is_duplicate = any(_normalize_action_value(item.surface) == _normalize_action_value(en_to_da_translation) for item in actions)
        if not is_duplicate:
            en_lemma = (en_to_da_lemma or en_to_da_translation).strip()
            actions.append(
                WordActionSuggestion(
                    action_type="add_as_new",
                    surface=en_to_da_translation,
                    lemma=en_lemma,
                    translation_label=en_to_da_translation,
                    direction="en_to_da",
                    direction_label="English -> Danish",
                    pos_tag=en_to_da_pos_tag,
                    morphology=en_to_da_morphology,
                    show_lemma=_normalize_action_value(en_to_da_translation) != _normalize_action_value(en_lemma),
                )
            )

    return actions

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.repositories.numbers_audio import NumbersAudioRepository
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.shared import _normalize_pronunciation_audio

NUMBER_TERMS = [
    "nul", "en", "to", "tre", "fire", "fem", "seks", "syv", "otte", "ni",
    "ti", "elleve", "tolv", "tretten", "fjorten", "femten",
    "seksten", "sytten", "atten", "nitten",
    "tyve", "tredive", "fyrre", "halvtreds", "tres", "halvfjerds", "firs", "halvfems",
]


@dataclass
class SeedNumbersAudioResult:
    generated: int
    skipped: int
    failed: int


def get_numbers_pronunciation_audio(term: str, db_path: Path) -> PronunciationAudio:
    normalized = term.strip().lower()
    if not normalized:
        raise ValueError("term is required")
    audio = NumbersAudioRepository(db_path).get(normalized)
    if audio is None:
        raise LookupError(f"No pronunciation stored for '{normalized}'")
    return audio


def seed_numbers_audio(
    tts_service: TTSService | None,
    db_path: Path,
    *,
    force: bool = False,
) -> SeedNumbersAudioResult:
    if tts_service is None:
        raise RuntimeError(
            "Text-to-speech is unavailable. Configure DANOTE_TTS_AZURE_API_KEY and DANOTE_TTS_AZURE_REGION."
        )
    repo = NumbersAudioRepository(db_path)
    generated = skipped = failed = 0
    for term in NUMBER_TERMS:
        if not force and repo.get(term) is not None:
            skipped += 1
            continue
        try:
            raw = tts_service.synthesize(term)
        except Exception:
            failed += 1
            continue
        if raw is None:
            failed += 1
            continue
        normalized = _normalize_pronunciation_audio(raw)
        repo.upsert(
            term=term,
            audio_bytes=normalized.audio_bytes,
            mime_type=normalized.mime_type,
            provider=getattr(tts_service, "provider", None),
            model=getattr(tts_service, "model", None),
        )
        generated += 1
    return SeedNumbersAudioResult(generated=generated, skipped=skipped, failed=failed)

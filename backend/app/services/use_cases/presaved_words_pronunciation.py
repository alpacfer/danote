from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.db.repositories.presaved_words_audio import PresavedWordsAudioRepository
from app.services.tts import PronunciationAudio, TTSService
from app.services.use_cases.wordbank.shared import _normalize_pronunciation_audio

PRESAVED_WORD_TERMS = [
    # Personal pronouns — nominative
    "jeg", "du", "han", "hun", "den", "det", "vi", "i", "de",
    # Personal pronouns — accusative/oblique
    "mig", "dig", "ham", "hende", "os", "jer", "dem", "sig",
    # Possessive pronouns
    "min", "mit", "mine", "din", "dit", "dine",
    "hans", "hendes", "dens", "dets",
    "sin", "sit", "sine",
    "vores", "jeres", "deres",
    # Demonstrative pronouns
    "denne", "dette", "disse",
    # Interrogative pronouns/determiners
    "hvem", "hvad", "hvilken", "hvilket", "hvilke", "hvis",
    # Relative pronouns
    "som", "der",
    # Indefinite pronouns
    "man", "nogen", "noget", "ingen", "intet",
    "alle", "enhver", "ethvert", "begge", "hinanden", "hverandre",
    # HV adverbs
    "hvor", "hvornår", "hvordan", "hvorfor",
    # Articles & gender — paradigm examples shown on the Articles & Gender page
    "en", "et", "-en", "-et", "-ne",
    "bil", "bilen", "biler", "bilerne",
    "hus", "huset", "huse", "husene",
    "dreng", "drengen", "drenge", "drengene",
    "kvinde", "kvinden", "kvinder", "kvinderne",
    # Prepositions
    "på", "til", "fra", "med", "af", "over", "under", "for", "om",
    "hos", "ved", "mod", "gennem", "efter", "før", "mellem", "uden",
    # Conjunctions (coordinating + subordinating; "i", "for", "der", "som",
    # "hvis", "før" already listed above)
    "og", "eller", "men", "så",
    "at", "fordi", "når", "da", "mens", "selvom", "inden",
    # Days of the week
    "mandag", "tirsdag", "onsdag", "torsdag", "fredag", "lørdag", "søndag",
    # Months
    "januar", "februar", "marts", "april", "maj", "juni",
    "juli", "august", "september", "oktober", "november", "december",
    # Seasons
    "forår", "sommer", "efterår", "vinter",
    # Ordinal numbers (cardinals already covered by the numbers seeder)
    "første", "anden", "tredje", "fjerde", "femte", "sjette",
    "syvende", "ottende", "niende", "tiende",
    "ellevte", "tolvte", "trettende", "tyvende", "tredivte",
    "hundrede", "tusinde",
    # Time expressions — single-word forms only; multi-word phrases like
    # "i går" are handled at the sentence-pronunciation layer.
    "altid", "ofte", "sjældent", "aldrig",
    "indtil", "siden",
]


@dataclass
class SeedPresavedWordsAudioResult:
    generated: int
    skipped: int
    failed: int


def get_presaved_words_pronunciation_audio(term: str, db_path: Path) -> PronunciationAudio:
    normalized = term.strip().lower()
    if not normalized:
        raise ValueError("term is required")
    audio = PresavedWordsAudioRepository(db_path).get(normalized)
    if audio is None:
        raise LookupError(f"No pronunciation stored for '{normalized}'")
    return audio


def seed_presaved_words_audio(
    tts_service: TTSService | None,
    db_path: Path,
    *,
    force: bool = False,
) -> SeedPresavedWordsAudioResult:
    if tts_service is None:
        raise RuntimeError(
            "Text-to-speech is unavailable. Configure DANOTE_TTS_AZURE_API_KEY and DANOTE_TTS_AZURE_REGION."
        )
    repo = PresavedWordsAudioRepository(db_path)
    generated = skipped = failed = 0
    for term in PRESAVED_WORD_TERMS:
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
    return SeedPresavedWordsAudioResult(generated=generated, skipped=skipped, failed=failed)

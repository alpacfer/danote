#!/usr/bin/env python3
"""Pregenerate Danish number pronunciation audio and store in the database."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.config import load_settings
from app.db.migrations import apply_migrations
from app.db.repositories.numbers_audio import NumbersAudioRepository
from app.services.tts import AzureSpeechTTSService
from app.services.use_cases.wordbank.shared import _normalize_pronunciation_audio

NUMBER_TERMS = [
    # 0-9
    "nul", "en", "to", "tre", "fire", "fem", "seks", "syv", "otte", "ni",
    # 10-19
    "ti", "elleve", "tolv", "tretten", "fjorten", "femten",
    "seksten", "sytten", "atten", "nitten",
    # tens 20-90
    "tyve", "tredive", "fyrre", "halvtreds", "tres", "halvfjerds", "firs", "halvfems",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Pregenerate Danish number pronunciation audio and store in the database.",
    )
    parser.add_argument("--api-key", default=None,
                        help="Azure TTS API key. Overrides DANOTE_TTS_AZURE_API_KEY from env.")
    parser.add_argument("--region", default=None,
                        help="Azure TTS region. Overrides DANOTE_TTS_AZURE_REGION from env.")
    parser.add_argument("--db-path", type=Path, default=None,
                        help="Database path override. Defaults to DANOTE_DB_PATH from env.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate and overwrite audio even if already stored.")
    args = parser.parse_args()

    settings = load_settings()
    db_path = args.db_path or settings.db_path
    api_key = args.api_key or settings.tts_azure_api_key
    region = args.region or settings.tts_azure_region

    if not api_key or not region:
        print("ERROR: Provide --api-key and --region (or set DANOTE_TTS_AZURE_API_KEY / DANOTE_TTS_AZURE_REGION).", file=sys.stderr)
        return 1

    apply_migrations(db_path)

    tts = AzureSpeechTTSService(
        api_key=api_key,
        region=region,
        endpoint=settings.tts_azure_endpoint,
        voice_name=settings.tts_azure_voice_name,
    )
    repo = NumbersAudioRepository(db_path)
    generated = skipped = failed = 0

    for term in NUMBER_TERMS:
        if not args.force and repo.get(term) is not None:
            print(f"  skip  {term}")
            skipped += 1
            continue
        raw = tts.synthesize(term)
        if raw is None:
            print(f"  FAIL  {term}  (synthesize returned None)", file=sys.stderr)
            failed += 1
            continue
        normalized = _normalize_pronunciation_audio(raw)
        repo.upsert(
            term=term,
            audio_bytes=normalized.audio_bytes,
            mime_type=normalized.mime_type,
            provider=tts.provider,
            model=tts.model,
        )
        print(f"   ok   {term}")
        generated += 1

    print(f"\nDone: {generated} generated, {skipped} skipped, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

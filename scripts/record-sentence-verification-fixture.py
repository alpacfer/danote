#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "test-data" / "fixtures" / "gemini" / "sentence_verification"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import load_settings
from app.services.sentence_verification import (  # noqa: E402
    GeminiSentenceVerificationService,
    SentenceVerificationResult,
    _build_prompt,
    _parse_result,
)


def _result_payload(result: SentenceVerificationResult) -> dict[str, object]:
    return {
        "is_valid": result.is_valid,
        "errors": [
            {
                "start": error.start,
                "end": error.end,
                "message": error.message,
            }
            for error in result.errors
        ],
        "corrected_text": result.corrected_text,
        "language": result.language,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Record a raw Gemini sentence verification response into a replay fixture.",
    )
    parser.add_argument(
        "--fixture-name",
        required=True,
        help="Fixture filename stem, for example partial-input-no-autocomplete.",
    )
    parser.add_argument(
        "--source-text",
        required=True,
        help="Sentence or phrase to send to Gemini.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"Directory for saved fixtures. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Gemini API key. Defaults to DANOTE_GEMINI_API_KEY settings lookup.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Gemini model name. Defaults to configured sentence verification model.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing fixture file.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    settings = load_settings()
    api_key = (
        args.api_key
        or settings.word_verification_gemini_api_key
        or settings.gemini_api_key
    )
    model = args.model or settings.word_verification_gemini_model or settings.gemini_model
    if not api_key:
        print("Missing Gemini API key. Set DANOTE_GEMINI_API_KEY or pass --api-key.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.fixture_name}.json"
    if output_path.exists() and not args.force:
        print(f"Refusing to overwrite existing fixture: {output_path}", file=sys.stderr)
        print("Pass --force to overwrite.", file=sys.stderr)
        return 1

    source_text = " ".join(str(args.source_text).strip().split())
    if not source_text:
        print("--source-text must not be empty.", file=sys.stderr)
        return 1

    service = GeminiSentenceVerificationService(api_key=api_key, model=model)
    prompt = _build_prompt(source_text)
    raw_response = service._generate_text(prompt)
    parsed_result = _parse_result(raw_response, source_text)
    payload = {
        "source_text": source_text,
        "raw_response": raw_response,
        "expected": _result_payload(parsed_result),
        "recording": {
            "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt": prompt,
            "parsed_at_record_time": _result_payload(parsed_result),
        },
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output_path)
    print("Fixture recorded. Edit the expected block if the normalized result should differ from the current parser output.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

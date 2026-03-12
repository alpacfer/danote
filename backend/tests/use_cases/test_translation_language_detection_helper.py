from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "use_cases"
        / "wordbank"
        / "collaborators"
        / "translation_language_detection.py"
    )
    spec = importlib.util.spec_from_file_location("translation_language_detection", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detect_word_language_marks_danish_chars() -> None:
    module = _load_module()
    response = module.detect_word_language("sø", detect_source_language=lambda _: None)
    assert response.language == "da"


def test_detect_word_language_uses_provider_signal() -> None:
    module = _load_module()
    response = module.detect_word_language("book", detect_source_language=lambda _: "en")
    assert response.language == "en"

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

try:
    import argostranslate.package as argos_package
    import argostranslate.translate as argos_translate
except ImportError:  # pragma: no cover - dependency wiring handled in runtime/tests
    argos_package = None
    argos_translate = None


class TranslationError(RuntimeError):
    """Raised when a translation provider cannot return a translation."""


class TranslationService(Protocol):
    def translate_da_to_en(self, text: str) -> str | None: ...


@dataclass
class ArgosTranslationService:
    """Danish->English translator backed by local Argos Translate models."""

    source_code: str = "da"
    target_code: str = "en"
    _translator: object | None = field(default=None, init=False, repr=False, compare=False)

    def _ensure_translator(self):
        if self._translator is not None:
            return self._translator
        if argos_package is None or argos_translate is None:
            raise TranslationError("Argos Translate is not installed in the backend environment.")

        try:
            source_lang = next(
                language for language in argos_translate.get_installed_languages() if language.code == self.source_code
            )
            target_lang = next(
                language for language in argos_translate.get_installed_languages() if language.code == self.target_code
            )
            self._translator = source_lang.get_translation(target_lang)
            return self._translator
        except Exception:
            pass

        try:
            argos_package.update_package_index()
            package = next(
                candidate
                for candidate in argos_package.get_available_packages()
                if candidate.from_code == self.source_code and candidate.to_code == self.target_code
            )
            download_path = package.download()
            argos_package.install_from_path(download_path)
            source_lang = next(
                language for language in argos_translate.get_installed_languages() if language.code == self.source_code
            )
            target_lang = next(
                language for language in argos_translate.get_installed_languages() if language.code == self.target_code
            )
            self._translator = source_lang.get_translation(target_lang)
            return self._translator
        except Exception as exc:
            raise TranslationError(f"Argos translation setup failed: {exc}") from exc

    def translate_da_to_en(self, text: str) -> str | None:
        normalized = text.strip()
        if not normalized:
            return None

        try:
            translated = self._ensure_translator().translate(normalized)
        except TranslationError:
            raise
        except Exception as exc:
            raise TranslationError(f"Argos translation request failed: {exc}") from exc

        cleaned = translated.strip() if isinstance(translated, str) else ""
        return cleaned or None

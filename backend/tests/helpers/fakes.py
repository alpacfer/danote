from __future__ import annotations

from app.nlp.adapter import NLPToken
from app.services.cor import COREntry
from app.services.cor_local import CORLocalEntry
from app.services.tts import PronunciationAudio


class FakeTranslationService:
    def __init__(
        self,
        mapping: dict[str, str],
        detected_languages: dict[str, str] | None = None,
        *,
        failing_inputs: set[str] | None = None,
        provider: str = "azure_translator",
    ):
        self._mapping = mapping
        self._detected_languages = detected_languages or {}
        self._failing_inputs = failing_inputs or set()
        self.provider = provider
        self.calls: list[str] = []

    def translate_da_to_en(self, text: str) -> str | None:
        self.calls.append(text)
        if text in self._failing_inputs:
            raise RuntimeError("azure unavailable")
        return self._mapping.get(text)

    def translate_da_to_en_batch(self, texts: list[str]) -> list[str | None]:
        return [self.translate_da_to_en(t) for t in texts]

    def translate_en_to_da(self, text: str) -> str | None:
        self.calls.append(text)
        return self._mapping.get(text)

    def detect_source_language(self, text: str) -> str | None:
        self.calls.append(text)
        return self._detected_languages.get(text)


class FakeNLPAdapter:
    def tokenize(self, text: str) -> list[NLPToken]:
        return [
            NLPToken(text="Hej", lemma="hej", pos="INTJ", morphology="PronType=Prs", is_punctuation=False),
            NLPToken(text=",", lemma=None, pos=None, morphology=None, is_punctuation=True),
            NLPToken(text=" ", lemma=None, pos=None, morphology=None, is_punctuation=False),
            NLPToken(text="bog", lemma="bog", pos="NOUN", morphology="Definite=Ind|Gender=Com", is_punctuation=False),
        ]

    def lemma_candidates_for_token(self, token: str) -> list[str]:
        return [token.lower()]

    def lemma_for_token(self, token: str) -> str | None:
        return token.lower()

    def metadata(self) -> dict[str, str]:
        return {"adapter": "fake"}


class FakeCORLexiconService:
    def __init__(self, mapping: dict[str, list[COREntry]]):
        self._mapping = {key.lower(): value for key, value in mapping.items()}

    def lookup_full_form(self, value: str) -> list[COREntry]:
        return list(self._mapping.get(value.lower(), []))


class FakeCORLocalLexiconService:
    def __init__(
        self,
        by_form: dict[str, list[CORLocalEntry]] | None = None,
        by_lemma_idx: dict[int, list[CORLocalEntry]] | None = None,
    ):
        self._by_form = {key.lower(): value for key, value in (by_form or {}).items()}
        self._by_lemma_idx = by_lemma_idx or {}

    def lookup_form(self, value: str, limit: int = 100) -> list[CORLocalEntry]:
        return list(self._by_form.get(value.lower(), []))[:limit]

    def lookup_lemma(self, lemma_idx: int, limit: int = 1000) -> list[CORLocalEntry]:
        return list(self._by_lemma_idx.get(lemma_idx, []))[:limit]

    def lookup_cor_id(self, cor_id: str) -> CORLocalEntry | None:
        normalized = cor_id.strip()
        if not normalized:
            return None
        for entries in self._by_form.values():
            for entry in entries:
                if entry.cor_id == normalized:
                    return entry
        for entries in self._by_lemma_idx.values():
            for entry in entries:
                if entry.cor_id == normalized:
                    return entry
        return None


class FakeVerificationService:
    provider = "gemini"
    reviewer_role = "Professional Danish Language Expert"

    def __init__(
        self,
        verdict: str = "verified",
        message: str = "Entry is consistent.",
        *,
        categories: tuple[str, ...] = (),
        recategorized_categories: tuple[str, ...] | None = None,
    ):
        self._verdict = verdict
        self._message = message
        self._categories = categories
        self._recategorized_categories = recategorized_categories
        self.calls = []
        self.category_calls = []

    def verify_word_entry(self, payload):
        self.calls.append(payload)

        class Result:
            def __init__(self, verdict: str, message: str, categories: tuple[str, ...]):
                self.verdict = verdict
                self.message = message
                self.categories = categories

        return Result(self._verdict, self._message, self._categories)

    def classify_word_categories(self, payload):
        self.category_calls.append(payload)

        class Result:
            def __init__(self, categories: tuple[str, ...]):
                self.categories = categories

        return Result(self._recategorized_categories or self._categories)


class FakeGeminiWordTranslationService:
    provider = "gemini_word_translation"

    def __init__(
        self,
        mapping: dict[tuple[str, str, str | None], str | None],
        *,
        batch_overrides: dict[tuple[str, str, str | None], str | None] | None = None,
    ):
        self._mapping = mapping
        self.calls: list[tuple[str, str, str | None]] = []
        self.batch_calls: list[list[tuple[str, str, str | None]]] = []
        self._batch_overrides = batch_overrides or {}

    def translate_word(self, payload) -> str | None:
        key = (payload.surface_form, payload.lemma, payload.gloss)
        self.calls.append(key)
        return self._mapping.get(key)

    def translate_words_batch(self, payloads) -> list[str | None]:
        keys = [(payload.surface_form, payload.lemma, payload.gloss) for payload in payloads]
        self.batch_calls.append(keys)
        return [
            self._batch_overrides.get(key, self._mapping.get(key))
            for key in keys
        ]


class FakeGeminiRelatedWordsService:
    provider = "gemini_related_words"

    def __init__(self, mapping: dict[str, list[tuple[str, str, str]]]):
        self._mapping = {key.lower(): value for key, value in mapping.items()}
        self.calls: list[str] = []

    def find_related_words(self, *, lemma: str):
        self.calls.append(lemma)

        class Result:
            def __init__(self, rows: list[tuple[str, str, str]]):
                self.items = [
                    type(
                        "RelatedWordItem",
                        (),
                        {
                            "lemma": item_lemma,
                            "english_translation": english_translation,
                            "pos_tag": pos_tag,
                        },
                    )()
                    for item_lemma, english_translation, pos_tag in rows
                ]

        return Result(self._mapping.get(lemma.lower(), []))


class FakeTTSService:
    provider = "gemini_tts"
    model = "gemini-2.5-flash-preview-tts"

    def __init__(self, mapping: dict[str, bytes]):
        self._mapping = mapping
        self.calls: list[str] = []

    def synthesize(self, text: str) -> PronunciationAudio | None:
        self.calls.append(text)
        data = self._mapping.get(text)
        if not data:
            return None
        return PronunciationAudio(audio_bytes=data, mime_type="audio/wav")

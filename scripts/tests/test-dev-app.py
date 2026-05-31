#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = ROOT_DIR / "scripts" / "dev-app.py"


def load_dev_app():
    spec = importlib.util.spec_from_file_location("dev_app", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load dev-app.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dev_app = load_dev_app()


class DevAppHelpersTest(unittest.TestCase):
    def test_parse_target_spec_handles_all_supported_shapes(self) -> None:
        self.assertEqual(dev_app.parse_target_spec("lemma"), dev_app.TargetSpec("lemma"))
        self.assertEqual(dev_app.parse_target_spec("meaning:42"), dev_app.TargetSpec("meaning", meaning_id=42))
        self.assertEqual(
            dev_app.parse_target_spec("surface:7:bogen"),
            dev_app.TargetSpec("surface", meaning_id=7, surface_form="bogen"),
        )
        self.assertEqual(
            dev_app.parse_target_spec("surface:root:lærer"),
            dev_app.TargetSpec("surface", meaning_id=None, surface_form="lærer"),
        )

    def test_collect_verification_targets_normalizes_nested_details(self) -> None:
        details = {
            "lemma": "bog",
            "verification": {"status": "verified", "message": "OK", "suggested_actions": []},
            "meaning_sections": [
                {
                    "id": 3,
                    "meaning_key": "book",
                    "english_translation": "book",
                    "verification": {
                        "status": "flagged",
                        "message": "Review needed.",
                        "suggested_actions": [{"action_type": "fix_translation", "english_translation": "book"}],
                    },
                    "surface_forms": [
                        {
                            "form": "bogen",
                            "verification": {
                                "status": "queued",
                                "message": "Queued",
                                "suggested_actions": [],
                            },
                        }
                    ],
                }
            ],
        }

        targets = dev_app.collect_verification_targets(details)

        self.assertEqual([target["kind"] for target in targets], ["lemma", "meaning", "surface"])
        self.assertEqual(targets[1]["meaning_id"], 3)
        self.assertEqual(targets[1]["suggested_action_count"], 1)
        self.assertEqual(targets[2]["stored_surface_form"], "bogen")

    def test_category_status_snapshot_summarizes_categories_and_queued_verification(self) -> None:
        details = {
            "lemma": "and",
            "categories": [],
            "meaning_sections": [
                {
                    "id": 130,
                    "meaning_key": "and",
                    "english_translation": "duck",
                    "categories": ["Animal", "Food"],
                    "verification": {"status": "verified", "completed_at": "2026-05-24T08:03:31Z"},
                    "surface_forms": [
                        {
                            "form": "anden",
                            "verification": {"status": "queued"},
                        }
                    ],
                }
            ],
        }

        snapshot = dev_app.category_status_snapshot(details, poll_index=2)

        self.assertEqual(snapshot["poll_index"], 2)
        self.assertEqual(snapshot["category_count"], 2)
        self.assertEqual(snapshot["queued_verification_count"], 1)
        self.assertEqual(snapshot["scopes"][1]["categories"], ["Animal", "Food"])
        self.assertEqual(snapshot["scopes"][2]["stored_surface_form"], "anden")

    def test_category_status_expectation_fails_when_final_snapshot_is_missing_category(self) -> None:
        args = argparse_namespace(lemma="and", polls=1, interval=0.0, expect_category=["Animal"])
        client = FakeDetailsClient({"lemma": "and", "categories": [], "surface_forms": []})

        with self.assertRaises(dev_app.DevAppError):
            dev_app.handle_wordbank_category_status(args, client)

    def test_find_verification_target_selects_actionable_surface(self) -> None:
        details = {
            "lemma": "bog",
            "meaning_sections": [
                {
                    "id": 3,
                    "meaning_key": "book",
                    "surface_forms": [
                        {
                            "form": "Bogen",
                            "verification": {
                                "status": "flagged",
                                "provider": "gemini",
                                "message": "Review needed.",
                                "suggested_actions": [{"action_type": "move_to_meaning_section", "target_meaning_id": 4}],
                            },
                        }
                    ],
                }
            ],
        }

        target = dev_app.find_verification_target(
            details,
            dev_app.TargetSpec("surface", meaning_id=3, surface_form="bogen"),
        )

        self.assertIsNotNone(target)
        self.assertEqual(target["verification"]["provider"], "gemini")

    def test_success_envelope_contains_last_request_and_timings(self) -> None:
        client = dev_app.ApiClient("http://example.test", timeout=1.0, token=None)
        client.timings.append(
            {
                "request": {"method": "GET", "path": "/api/health"},
                "status": 200,
                "elapsed_ms": 1.25,
            }
        )

        envelope = dev_app.success_envelope("health", client, {"status": "ok"})

        self.assertTrue(envelope["ok"])
        self.assertEqual(envelope["request"], {"method": "GET", "path": "/api/health"})
        self.assertEqual(envelope["response"], {"status": "ok"})
        self.assertEqual(envelope["timings_ms"][0]["status"], 200)

    def test_timing_reports_backend_processing_and_client_overhead(self) -> None:
        timing = dev_app._timing(
            dev_app.RequestSpec("GET", "/api/health"),
            12.5,
            status=200,
            headers={"X-Process-Time-Ms": "10.25"},
        )

        self.assertEqual(timing["backend_process_ms"], 10.25)
        self.assertEqual(timing["client_overhead_ms"], 2.25)

    def test_cold_cache_requires_enabled_admin_endpoint(self) -> None:
        with self.assertRaisesRegex(dev_app.DevAppError, "DANOTE_SEARCH_ADMIN_ENABLED=1"):
            dev_app.clear_search_cache(FakeDisabledSearchAdminClient())

    def test_search_profile_decision_marks_sentence_and_short_words(self) -> None:
        self.assertEqual(dev_app.search_flow_decision("jeg er glad")["skip_reason"], "sentence_mode")
        self.assertEqual(dev_app.search_flow_decision("i")["skip_reason"], "too_short")
        self.assertTrue(dev_app.search_flow_decision("book")["single_word_lookup"])
        self.assertEqual(dev_app.search_flow_decision("book", language_mode="en")["language_mode"], "en")

    def test_search_profile_run_reports_waterfall_counts_and_skip(self) -> None:
        client = FakeProfileClient(
            {
                ("GET", "/api/wordbank/search", "language=en&query=book"): {"items": []},
                ("GET", "/api/wordbank/search/en-form", "form=book&include_translations=True"): {
                    "form": "book",
                    "groups": [{"lemma": "book", "pos_ud": "NOUN", "danish_translation": "bog", "senses": []}],
                },
                ("GET", "/api/wordbank/search/cor-form", "form=bog&include_translations=False"): {
                    "form": "bog",
                    "groups": [{"variants": [{"cor_id": "COR.BOG"}]}],
                },
                ("POST", "/api/wordbank/search/cor-form-batch", ""): {
                    "items": [{"form": "bog", "groups": [{"variants": [{"cor_id": "COR.BOG"}]}]}],
                },
            }
        )

        run = dev_app.run_search_profile_once(
            client,
            query="book",
            normalized_query="book",
            decision=dev_app.search_flow_decision("book", language_mode="en"),
            run_index=0,
            cold_cache=False,
            include_resolve=False,
            use_cor_batch=True,
        )

        self.assertTrue(run["flow"]["skipped_direct_cor_full"])
        self.assertEqual(run["flow"]["language_mode"], "en")
        self.assertEqual(run["counts"]["en_groups"], 1)
        self.assertEqual(run["counts"]["translated_cor_variants"], 1)
        self.assertNotIn("cor_full", {phase["name"] for phase in run["phases"]})

    def test_search_mode_check_prompts_for_opposite_english_word(self) -> None:
        client = FakeProfileClient(
            {
                ("GET", "/api/wordbank/search", "language=en&query=book"): {"items": []},
                ("GET", "/api/wordbank/search/en-form", "form=book&include_translations=False"): {
                    "form": "book",
                    "groups": [{"lemma": "book", "pos_ud": "NOUN", "danish_translation": "bog"}],
                },
            }
        )

        result = dev_app.run_search_mode_check(client, query="book", mode="da")

        self.assertTrue(result["should_prompt"])
        self.assertEqual(result["target_mode"], "en")
        self.assertEqual(result["query_kind"], "word")
        self.assertEqual(result["reason"], "opposite_en_dictionary_match")
        self.assertEqual(
            {phase["name"] for phase in result["phases"]},
            {"opposite_wordbank", "opposite_en_form"},
        )

    def test_search_mode_check_does_not_prompt_for_exact_danish_cor_with_loose_saved_match(self) -> None:
        client = FakeProfileClient(
            {
                ("GET", "/api/wordbank/search/cor-form", "form=lave&include_translations=False"): {
                    "form": "lave",
                    "groups": [{"variants": [{"form": "lave", "cor_id": "COR.LAVE"}]}],
                },
                ("GET", "/api/wordbank/search", "language=en&query=lave"): {
                    "items": [{"lemma": "holde", "matched_via": "english_gloss"}],
                },
                ("GET", "/api/wordbank/search/en-form", "form=lave&include_translations=False"): {
                    "form": "lave",
                    "groups": [],
                },
            }
        )

        result = dev_app.run_search_mode_check(client, query="lave", mode="da")

        self.assertFalse(result["should_prompt"])
        self.assertEqual(result["reason"], "current_cor_exact_form")
        self.assertTrue(result["evidence"]["current_cor_exact_form"])

    def test_search_mode_check_prompts_for_opposite_danish_exact_cor(self) -> None:
        client = FakeProfileClient(
            {
                ("GET", "/api/wordbank/search", "language=da&query=bog"): {"items": []},
                ("GET", "/api/wordbank/search/cor-form", "form=bog&include_translations=False"): {
                    "form": "bog",
                    "groups": [{"variants": [{"form": "bog", "cor_id": "COR.BOG"}]}],
                },
            }
        )

        result = dev_app.run_search_mode_check(client, query="bog", mode="en")

        self.assertTrue(result["should_prompt"])
        self.assertEqual(result["target_mode"], "da")
        self.assertEqual(result["reason"], "opposite_cor_exact_form")
        self.assertTrue(result["evidence"]["opposite_cor_exact_form"])

    def test_find_cor_sense_variant_can_disambiguate_by_cor_id(self) -> None:
        cor_form = {
            "groups": [
                {
                    "pos_tag": "VERB",
                    "variants": [
                        {"meaning_key": "walk", "pos_tag": "VERB", "cor_id": "COR.30234.200.01"},
                        {"meaning_key": "walk", "pos_tag": "VERB", "cor_id": "COR.30234.209.01"},
                    ],
                }
            ]
        }

        _group, variant = dev_app._find_cor_sense_variant(
            cor_form,
            surface="gå",
            meaning_key="walk",
            pos_tag="VERB",
            cor_id="COR.30234.209.01",
        )

        self.assertEqual(variant["cor_id"], "COR.30234.209.01")

    def test_search_mode_check_uses_neutral_fast_sentence_preview(self) -> None:
        client = FakeProfileClient(
            {
                ("POST", "/api/sentencebank/search-preview", ""): {
                    "status": "preview",
                    "query_language": "en",
                    "source_text": "jeg er glad",
                    "english_translation": "I am happy",
                    "is_valid": True,
                    "errors": [],
                    "message": None,
                },
            }
        )

        result = dev_app.run_search_mode_check(client, query="I am happy", mode="da")

        self.assertTrue(result["should_prompt"])
        self.assertEqual(result["query_kind"], "sentence")
        self.assertEqual(result["reason"], "en_sentence_detected")
        request = result["phases"][0]["request"]
        self.assertEqual(request["body"], {"source_text": "I am happy", "fast": True, "language_mode": None})

    def test_search_mode_check_overrides_ascii_danish_sentence_misdetection(self) -> None:
        client = FakeProfileClient(
            {
                ("POST", "/api/sentencebank/search-preview", ""): {
                    "status": "preview",
                    "query_language": "en",
                    "source_text": "hunden sover",
                    "english_translation": "the dog sleeps",
                    "is_valid": True,
                    "errors": [],
                    "message": None,
                },
            }
        )

        danish_mode = dev_app.run_search_mode_check(client, query="hunden sover", mode="da")
        english_mode = dev_app.run_search_mode_check(client, query="hunden sover", mode="en")

        self.assertFalse(danish_mode["should_prompt"])
        self.assertTrue(english_mode["should_prompt"])
        self.assertEqual(english_mode["evidence"]["effective_sentence_language"], "da")

    def test_search_mode_check_skips_empty_number_and_short_queries(self) -> None:
        client = FakeProfileClient({})

        self.assertEqual(dev_app.run_search_mode_check(client, query="", mode="da")["reason"], "empty_query")
        self.assertEqual(dev_app.run_search_mode_check(client, query="21", mode="da")["query_kind"], "number")
        self.assertEqual(dev_app.run_search_mode_check(client, query="a", mode="da")["reason"], "too_short")

    def test_search_and_wordcard_display_helpers_match_parenthetical_gloss(self) -> None:
        group = {"gloss": "jordlag", "pos_tag": "NOUN"}
        variant = {
            "lemma_translation": "mother",
            "saveable_translation": "mother",
            "gloss_translation": "soil layer",
            "alternative_translations": [],
        }
        section = {
            "english_translation": "mother",
            "gloss_translation": "soil layer",
            "additional_translations": [],
        }

        self.assertEqual(dev_app._search_variant_display(group, variant), "mother (soil layer)")
        self.assertEqual(dev_app._wordcard_section_display(section), "mother (soil layer)")

    def test_verify_saved_display_fails_when_displays_diverge(self) -> None:
        client = FakeVerifySavedDisplayClient(
            section={
                "id": 7,
                "meaning_key": "enough",
                "pos_tag": "ADV",
                "english_translation": "probably",
                "gloss_translation": "in all likelihood",
                "additional_translations": [],
            }
        )

        with self.assertRaises(dev_app.DevAppError):
            dev_app.handle_wordbank_verify_saved_display(
                argparse_namespace(surface="nok", meaning_key="enough", pos_tag="ADV", lemma=None),
                client,
            )


class FakeProfileClient:
    def __init__(self, responses):
        self.responses = responses
        self.timings = []

    def request(self, spec):
        params = spec.params or {}
        interesting = {
            key: value
            for key, value in params.items()
            if key in {"query", "form", "include_translations", "language"}
        }
        key = (
            spec.method,
            spec.path,
            "&".join(f"{name}={interesting[name]}" for name in sorted(interesting)),
        )
        self.timings.append({"request": dev_app.request_payload(spec), "status": 200, "elapsed_ms": 0.1})
        try:
            return self.responses[key]
        except KeyError as exc:
            raise AssertionError(f"Unexpected request: {key}") from exc


class FakeDisabledSearchAdminClient:
    def request(self, spec):
        raise dev_app.DevAppError(
            "HTTP 404: Not Found",
            status=404,
            body='{"detail":"Not found"}',
            request=dev_app.request_payload(spec),
        )


class FakeDetailsClient:
    def __init__(self, details):
        self.details = details
        self.timings = []

    def request(self, spec):
        self.timings.append({"request": dev_app.request_payload(spec), "status": 200, "elapsed_ms": 0.1})
        return self.details


class FakeVerifySavedDisplayClient:
    def __init__(self, *, section):
        self.section = section
        self.timings = []

    def request(self, spec):
        self.timings.append({"request": dev_app.request_payload(spec), "status": 200, "elapsed_ms": 0.1})
        if spec.path == "/api/wordbank/search/cor-form":
            return {
                "form": "nok",
                "groups": [
                    {
                        "lemma": "nok",
                        "gloss": "i tilstrækkelig grad",
                        "pos_tag": "ADV",
                        "variants": [
                            {
                                "form": "nok",
                                "lemma": "nok",
                                "cor_id": "COR.10200.900.01",
                                "lemma_idx": 10200,
                                "meaning_key": "enough",
                                "pos_tag": "ADV",
                                "gloss": "i tilstrækkelig grad",
                                "english_gloss": "to a sufficient degree",
                                "gloss_translation": "to a sufficient degree",
                                "lemma_translation": "enough",
                                "saveable_translation": "enough",
                                "alternative_translations": [],
                            }
                        ],
                    }
                ],
            }
        if spec.path == "/api/wordbank/lexemes":
            return {
                "stored_lemma": "nok",
                "meaning": {"id": 7, "meaning_key": "enough", "english_translation": "enough"},
            }
        if spec.path == "/api/wordbank/lemmas/nok":
            return {"lemma": "nok", "meaning_sections": [self.section]}
        raise AssertionError(f"Unexpected request: {spec.method} {spec.path}")


def argparse_namespace(**kwargs):
    return type("Args", (), kwargs)()


if __name__ == "__main__":
    unittest.main()

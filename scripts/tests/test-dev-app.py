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

    def test_search_profile_decision_marks_sentence_and_short_words(self) -> None:
        self.assertEqual(dev_app.search_flow_decision("jeg er glad")["skip_reason"], "sentence_mode")
        self.assertEqual(dev_app.search_flow_decision("i")["skip_reason"], "too_short")
        self.assertTrue(dev_app.search_flow_decision("book")["single_word_lookup"])

    def test_search_profile_run_reports_waterfall_counts_and_skip(self) -> None:
        client = FakeProfileClient(
            {
                ("GET", "/api/wordbank/search", "query=book"): {"items": []},
                ("GET", "/api/wordbank/search/cor-form", "form=book&include_translations=False"): {
                    "form": "book",
                    "groups": [
                        {
                            "lemma": "booke",
                            "gloss": None,
                            "pos_tag": "VERB",
                            "variants": [{"form": "book", "lemma": "booke", "gloss": None}],
                        }
                    ],
                },
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
            decision=dev_app.search_flow_decision("book"),
            run_index=0,
            cold_cache=False,
            include_resolve=False,
            use_cor_batch=True,
        )

        self.assertTrue(run["flow"]["skipped_direct_cor_full"])
        self.assertEqual(run["counts"]["en_groups"], 1)
        self.assertEqual(run["counts"]["translated_cor_variants"], 1)
        self.assertNotIn("cor_full", {phase["name"] for phase in run["phases"]})


class FakeProfileClient:
    def __init__(self, responses):
        self.responses = responses
        self.timings = []

    def request(self, spec):
        params = spec.params or {}
        interesting = {
            key: value
            for key, value in params.items()
            if key in {"query", "form", "include_translations"}
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


class FakeDetailsClient:
    def __init__(self, details):
        self.details = details
        self.timings = []

    def request(self, spec):
        self.timings.append({"request": dev_app.request_payload(spec), "status": 200, "elapsed_ms": 0.1})
        return self.details


def argparse_namespace(**kwargs):
    return type("Args", (), kwargs)()


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

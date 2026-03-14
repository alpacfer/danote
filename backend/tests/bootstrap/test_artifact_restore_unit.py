from __future__ import annotations

from pathlib import Path

from tests.helpers.artifact_restore import capture_file_snapshot, restore_file_snapshot


def test_restore_file_snapshot_restores_original_contents(tmp_path: Path) -> None:
    target = tmp_path / "artifacts" / "gemini-applied-changes.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("original\n", encoding="utf-8")

    snapshot = capture_file_snapshot(target)

    target.write_text("mutated\n", encoding="utf-8")
    restore_file_snapshot(snapshot)

    assert target.read_text(encoding="utf-8") == "original\n"


def test_restore_file_snapshot_removes_file_that_did_not_exist(tmp_path: Path) -> None:
    target = tmp_path / "artifacts" / "gemini-applied-changes.jsonl"
    snapshot = capture_file_snapshot(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("generated\n", encoding="utf-8")
    restore_file_snapshot(snapshot)

    assert not target.exists()

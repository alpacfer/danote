from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileSnapshot:
    path: Path
    existed: bool
    contents: bytes | None


def capture_file_snapshot(path: Path) -> FileSnapshot:
    if path.exists():
        return FileSnapshot(path=path, existed=True, contents=path.read_bytes())
    return FileSnapshot(path=path, existed=False, contents=None)


def restore_file_snapshot(snapshot: FileSnapshot) -> None:
    if snapshot.existed:
        snapshot.path.parent.mkdir(parents=True, exist_ok=True)
        expected_contents = snapshot.contents or b""
        current_contents = snapshot.path.read_bytes() if snapshot.path.exists() else None
        if current_contents != expected_contents:
            snapshot.path.write_bytes(expected_contents)
        return

    if snapshot.path.exists():
        snapshot.path.unlink()

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT_DIR / "test-data" / "benchmark-reports"


def append_benchmark_report(*, benchmark: str, run_data: dict[str, Any]) -> Path:
    """Append one benchmark run to a persistent JSON history file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{benchmark}-report.json"

    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any]
    if report_path.exists():
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        runs = payload.get("runs", [])
        if not isinstance(runs, list):
            runs = []
    else:
        runs = []
        payload = {
            "benchmark": benchmark,
            "created_at": now,
            "runs": runs,
        }

    runs.append({"timestamp": now, **run_data})
    payload["updated_at"] = now
    payload["runs"] = runs

    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path

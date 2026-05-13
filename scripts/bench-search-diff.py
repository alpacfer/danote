#!/usr/bin/env python3
"""Quality-diff two search benchmark JSON reports."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: scripts/bench-search-diff.py BASELINE CANDIDATE", file=sys.stderr)
        return 2
    baseline = _load_report(Path(sys.argv[1]))
    candidate = _load_report(Path(sys.argv[2]))
    diffs = _diff_reports(baseline, candidate)
    if diffs:
        for diff in diffs:
            print(diff)
        return 1
    print("quality diff: OK")
    return 0


def _load_report(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_reports(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[str]:
    diffs: list[str] = []
    baseline_runs = _first_run_by_query(baseline)
    candidate_runs = _first_run_by_query(candidate)
    for query in sorted(set(baseline_runs) | set(candidate_runs)):
        if query not in baseline_runs:
            diffs.append(f"{query}: missing from baseline")
            continue
        if query not in candidate_runs:
            diffs.append(f"{query}: missing from candidate")
            continue
        base_run = baseline_runs[query]
        cand_run = candidate_runs[query]
        base_en = _en_tuples(base_run)
        cand_en = _en_tuples(cand_run)
        if base_en != cand_en:
            diffs.append(f"{query}: en-form tuples differ\n  baseline={base_en}\n  candidate={cand_en}")
        base_cor = _cor_sets(base_run)
        cand_cor = _cor_sets(cand_run)
        if base_cor != cand_cor:
            diffs.append(f"{query}: cor-form kept ids differ\n  baseline={base_cor}\n  candidate={cand_cor}")
    return diffs


def _first_run_by_query(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    runs: dict[str, dict[str, Any]] = {}
    for run in report.get("runs") or []:
        query = str(run.get("query") or "")
        if query and query not in runs:
            runs[query] = run
    return runs


def _en_tuples(run: dict[str, Any]) -> list[tuple[str, str, str | None]]:
    payload = ((run.get("responses") or {}).get("en_form") or {})
    tuples: list[tuple[str, str, str | None]] = []
    for group in payload.get("groups") or []:
        tuples.append((
            str(group.get("lemma") or ""),
            str(group.get("pos_ud") or ""),
            group.get("danish_translation"),
        ))
    return tuples


def _cor_sets(run: dict[str, Any]) -> dict[str, list[str]]:
    payloads = ((run.get("responses") or {}).get("cor_forms") or {})
    result: dict[str, list[str]] = {}
    for form, payload in payloads.items():
        ids: set[str] = set()
        for group in payload.get("groups") or []:
            for variant in group.get("variants") or []:
                cor_id = variant.get("cor_id")
                if isinstance(cor_id, str):
                    ids.add(cor_id)
        result[str(form)] = sorted(ids)
    return result


if __name__ == "__main__":
    sys.exit(main())

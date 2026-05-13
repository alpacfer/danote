#!/usr/bin/env python3
"""Benchmark sidebar-style English search latency against a live backend."""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_HOSTS = ("127.0.0.1", "localhost")
DEFAULT_PORTS = (8000, 8001, 8002)
HTTP_TIMEOUT_SECONDS = 60.0
REPORT_DIR = Path("backend/test-data/benchmark-reports")


def main() -> int:
    args = _parse_args()
    base_url = _resolve_base_url(args)
    if base_url is None:
        print("Could not locate a running backend. Start `make dev` first, or pass --host/--port.", file=sys.stderr)
        return 2

    runs: list[dict[str, Any]] = []
    for query in args.queries:
        for run_index in range(args.runs):
            cold = run_index < args.cold_runs
            if cold:
                _clear_search_cache(base_url)
            runs.append(_run_query(base_url, query, run_index=run_index, cold=cold, use_cor_batch=args.cor_batch))

    report = {
        "label": args.label,
        "backend": base_url,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "queries": args.queries,
        "runs": runs,
        "summary": _summarize(runs),
    }
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    label = args.label.replace("/", "-").replace(" ", "_")
    default_name = f"search-latency-{label}.json" if label else f"search-latency-{int(time.time())}.json"
    output_path = Path(args.output) if args.output else REPORT_DIR / default_name
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", nargs="+", help="English queries to benchmark.")
    parser.add_argument("--runs", type=int, default=5, help="Runs per query.")
    parser.add_argument("--cold-runs", type=int, default=0, help="Clear cache before the first N runs per query.")
    parser.add_argument("--label", default="", help="Report label, e.g. P0+P1.")
    parser.add_argument("--output", help="Explicit output report path.")
    parser.add_argument("--host", help="Backend host.")
    parser.add_argument("--port", type=int, help="Backend port.")
    parser.add_argument(
        "--legacy-cor-loop",
        dest="cor_batch",
        action="store_false",
        help="Use one filtered cor-form GET per Danish translation instead of cor-form-batch.",
    )
    parser.set_defaults(cor_batch=True)
    return parser.parse_args()


def _run_query(base_url: str, query: str, *, run_index: int, cold: bool, use_cor_batch: bool) -> dict[str, Any]:
    timings: list[dict[str, Any]] = []
    total_start = time.perf_counter()
    en_payload = _get_json(base_url, "/api/wordbank/search/en-form", {"form": query}, timings)
    groups = en_payload.get("groups") or []
    translation_items = _translation_items(query, groups)

    cor_payloads: dict[str, Any] = {}
    if use_cor_batch and translation_items:
        batch_payload = _post_json(
            base_url,
            "/api/wordbank/search/cor-form-batch",
            {
                "limit": 100,
                "include_translations": False,
                "items": translation_items,
            },
            timings,
        )
        for item, payload in zip(translation_items, batch_payload.get("items") or []):
            cor_payloads[item["form"]] = payload
    else:
        for item in translation_items:
            params = {
                "form": item["form"],
                "limit": "100",
                "include_translations": "false",
                "en_query": item["en_query"],
            }
            if item.get("en_pos_ud"):
                params["en_pos_ud"] = item["en_pos_ud"]
            cor_payloads[item["form"]] = _get_json(base_url, "/api/wordbank/search/cor-form", params, timings)

    total_wall_ms = (time.perf_counter() - total_start) * 1000
    return {
        "query": query,
        "run_index": run_index,
        "cold": cold,
        "total_wall_ms": total_wall_ms,
        "sum_http_ms": sum(item["duration_ms"] for item in timings),
        "timings": timings,
        "responses": {
            "en_form": en_payload,
            "cor_forms": cor_payloads,
        },
    }


def _translation_items(query: str, groups: list[dict[str, Any]]) -> list[dict[str, str | None]]:
    pos_by_key: dict[str, set[str]] = {}
    label_by_key: dict[str, str] = {}
    for group in groups:
        translation = " ".join(str(group.get("danish_translation") or "").strip().split())
        if not translation:
            continue
        key = translation.lower()
        label_by_key.setdefault(key, translation)
        pos = str(group.get("pos_ud") or "").strip().upper()
        if pos:
            pos_by_key.setdefault(key, set()).add(pos)
    return [
        {
            "form": label,
            "en_query": query,
            "en_pos_ud": ",".join(sorted(pos_by_key.get(key, set()))) or None,
        }
        for key, label in label_by_key.items()
    ]


def _summarize(runs: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for query in sorted({run["query"] for run in runs}):
        query_runs = [run for run in runs if run["query"] == query]
        totals = [run["total_wall_ms"] for run in query_runs]
        http_sums = [run["sum_http_ms"] for run in query_runs]
        summary[query] = {
            "runs": len(query_runs),
            "p50_wall_ms": statistics.median(totals),
            "p95_wall_ms": _percentile(totals, 0.95),
            "p50_sum_http_ms": statistics.median(http_sums),
            "p95_sum_http_ms": _percentile(http_sums, 0.95),
            "total_wall_ms": sum(totals),
        }
    return summary


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
    return ordered[index]


def _get_json(base_url: str, path: str, params: dict[str, str], timings: list[dict[str, Any]]) -> dict[str, Any]:
    url = f"{base_url}{path}?{urllib.parse.urlencode(params)}"
    return _request_json(url, timings, label=_label(path, params))


def _post_json(base_url: str, path: str, payload: dict[str, Any], timings: list[dict[str, Any]]) -> dict[str, Any]:
    url = f"{base_url}{path}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    return _request_json(request, timings, label=path.rsplit("/", 1)[-1])


def _request_json(target: str | urllib.request.Request, timings: list[dict[str, Any]], *, label: str) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(target, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} for {label}: {body[:300]}") from exc
    duration_ms = (time.perf_counter() - started) * 1000
    timings.append({"label": label, "duration_ms": duration_ms})
    return payload


def _label(path: str, params: dict[str, str]) -> str:
    endpoint = path.rsplit("/", 1)[-1]
    form = params.get("form")
    if form:
        return f"{endpoint} {form}"
    return endpoint


def _clear_search_cache(base_url: str) -> None:
    request = urllib.request.Request(f"{base_url}/api/admin/clear-search-cache", data=b"{}", method="POST")
    try:
        urllib.request.urlopen(request, timeout=10).close()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
        return


def _resolve_base_url(args: argparse.Namespace) -> str | None:
    if args.host or args.port:
        return _probe(f"http://{args.host or '127.0.0.1'}:{args.port or 8000}")
    detected = _discover_uvicorn_port()
    candidates: list[tuple[str, int]] = []
    if detected:
        candidates.extend((host, detected) for host in DEFAULT_HOSTS)
    candidates.extend((host, port) for host in DEFAULT_HOSTS for port in DEFAULT_PORTS)
    for host, port in candidates:
        url = _probe(f"http://{host}:{port}")
        if url:
            return url
    return None


def _discover_uvicorn_port() -> int | None:
    try:
        out = subprocess.check_output(["ps", "-Ao", "command="], text=True, timeout=2)
    except (subprocess.SubprocessError, OSError):
        return None
    for line in out.splitlines():
        if "uvicorn" not in line or "app.main:app" not in line:
            continue
        bits = line.split()
        for index, bit in enumerate(bits[:-1]):
            if bit == "--port" and bits[index + 1].isdigit():
                return int(bits[index + 1])
    return None


def _probe(base: str) -> str | None:
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=2) as response:
            return base if response.status == 200 else None
    except (urllib.error.URLError, TimeoutError, OSError):
        return None


if __name__ == "__main__":
    sys.exit(main())

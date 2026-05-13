#!/usr/bin/env python3
"""Trace a sidebar-style search against the live backend.

Locates the running uvicorn (no need to know the port), then walks through
the same EN → DA → COR pipeline the sidebar performs, printing each stage
with side-by-side before/after for the Gemini sense filter so you can see
exactly which variants survived and why.

Examples (run from repo root):

    scripts/dev-search-debug.py card
    scripts/dev-search-debug.py "table"
    scripts/dev-search-debug.py --da bord       # direct Danish search
    scripts/dev-search-debug.py --host 127.0.0.1 --port 8001 run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_HOSTS = ("127.0.0.1", "localhost")
DEFAULT_PORTS = (8000, 8001, 8002)
HTTP_TIMEOUT_SECONDS = 30.0

# Collected per-call timings, plus the totals printed at the end.
TIMINGS: list[tuple[str, float]] = []


def main() -> int:
    args = _parse_args()
    base_url = _resolve_base_url(args)
    if base_url is None:
        print(
            "Could not locate a running backend. Start `make dev` first, or pass --host/--port.",
            file=sys.stderr,
        )
        return 2
    print(f"[backend] {base_url}\n")

    query = args.query.strip()
    if not query:
        print("query is empty", file=sys.stderr)
        return 2

    total_start = time.perf_counter()
    if args.da:
        _print_section(f"Direct Danish COR lookup for {query!r}")
        _print_cor_form(base_url, query, en_query=None)
        _print_timings(total_start)
        return 0

    en_groups = _print_en_resolve(base_url, query)
    if not en_groups:
        print("\nNo English groups; nothing more to trace.")
        _print_timings(total_start)
        return 0

    _trace_translation_keys(base_url, query, en_groups)
    _print_timings(total_start)
    return 0


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", help="The word to search for (English by default, or Danish with --da).")
    parser.add_argument("--host", help="Backend host (default: auto-detect or 127.0.0.1).")
    parser.add_argument("--port", type=int, help="Backend port (default: auto-detect or 8000).")
    parser.add_argument(
        "--da",
        action="store_true",
        help="Skip the EN flow and hit the COR lookup directly with the given Danish form.",
    )
    return parser.parse_args()


# ----------------------------------------------------------------------
# Backend discovery
# ----------------------------------------------------------------------


def _resolve_base_url(args: argparse.Namespace) -> str | None:
    if args.host or args.port:
        host = args.host or "127.0.0.1"
        port = args.port or 8000
        return _probe(f"http://{host}:{port}")
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
        match = re.search(r"--port\s+(\d+)", line)
        if match:
            return int(match.group(1))
    return None


def _probe(base: str) -> str | None:
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=2) as response:
            if response.status == 200:
                return base
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    return None


# ----------------------------------------------------------------------
# Tracing
# ----------------------------------------------------------------------


def _print_en_resolve(base_url: str, query: str) -> list[dict[str, Any]]:
    _print_section(f"EN resolve for {query!r}")
    payload = _get_json(base_url, "/api/wordbank/search/en-form", {"form": query})
    if not payload:
        print("  (no payload)")
        return []
    groups = payload.get("groups") or []
    if not groups:
        print("  (no EN groups — query may not be in the EN lexicon)")
        return []
    for group in groups:
        pos = group.get("pos_ud")
        lemma = group.get("lemma")
        translation = group.get("danish_translation") or "—"
        meaning = group.get("meaning_description") or ""
        suffix = f"  // {meaning}" if meaning else ""
        print(f"  {pos:<5} {lemma:<20} → {translation}{suffix}")
    return groups


def _trace_translation_keys(base_url: str, query: str, en_groups: list[dict[str, Any]]) -> None:
    # Collect all source POSes per translation key — multiple EN POS groups can share
    # a Danish translation. The backend filter is sharpest when given every POS that
    # claims this translation.
    pos_by_key: dict[str, list[str]] = {}
    label_by_key: dict[str, str] = {}
    for group in en_groups:
        translation = (group.get("danish_translation") or "").strip()
        if not translation:
            continue
        key = translation.lower()
        pos = (group.get("pos_ud") or "").strip().upper()
        if pos and pos not in pos_by_key.setdefault(key, []):
            pos_by_key[key].append(pos)
        label_by_key.setdefault(key, translation)
    for key, label in label_by_key.items():
        pos_list = pos_by_key.get(key, [])
        pos_param = ",".join(sorted(pos_list)) if pos_list else None
        pos_display = "+".join(pos_list) if pos_list else "?"
        _print_section(f"COR lookup for {label!r} (EN POS hint {pos_display})")
        unfiltered = _fetch_cor_variants(base_url, label, en_query=None, en_pos_ud=None)
        filtered = _fetch_cor_variants(base_url, label, en_query=query, en_pos_ud=pos_param)
        _render_filter_diff(unfiltered, filtered)


def _fetch_cor_variants(
    base_url: str,
    form: str,
    *,
    en_query: str | None,
    en_pos_ud: str | None = None,
) -> list[dict[str, Any]]:
    params = {"form": form, "limit": "100", "include_translations": "false"}
    if en_query:
        params["en_query"] = en_query
    if en_pos_ud:
        params["en_pos_ud"] = en_pos_ud
    payload = _get_json(base_url, "/api/wordbank/search/cor-form", params)
    if not payload:
        return []
    flattened: list[dict[str, Any]] = []
    for group in payload.get("groups") or []:
        for variant in group.get("variants") or []:
            flattened.append(
                {
                    "cor_id": variant.get("cor_id"),
                    "lemma": variant.get("lemma"),
                    "pos_tag": variant.get("pos_tag"),
                    "form": variant.get("form"),
                    "gram_raw": variant.get("gram_raw"),
                    "gloss": group.get("gloss"),
                }
            )
    return flattened


def _render_filter_diff(unfiltered: list[dict[str, Any]], filtered: list[dict[str, Any]]) -> None:
    if not unfiltered:
        print("  (no variants returned)")
        return
    filtered_ids = {variant["cor_id"] for variant in filtered}
    print(f"  {'kept' if filtered_ids else '✗':<5}  {'cor_id':<22} {'lemma':<12} {'pos':<5} {'form':<10} gram")
    print(f"  {'----':<5}  {'-' * 22} {'-' * 12} {'-' * 5} {'-' * 10} ----")
    for variant in unfiltered:
        kept = variant["cor_id"] in filtered_ids
        marker = "✓" if kept else "✗"
        gloss = variant.get("gloss") or ""
        gloss_suffix = f"   « {gloss}" if gloss else ""
        print(
            f"  {marker:<5}  {variant['cor_id']:<22} {variant['lemma']:<12} "
            f"{variant['pos_tag'] or '?':<5} {variant['form']:<10} {variant['gram_raw']}{gloss_suffix}"
        )
    dropped = [v for v in unfiltered if v["cor_id"] not in filtered_ids]
    if dropped:
        print(f"  filter dropped {len(dropped)}/{len(unfiltered)}")
    else:
        print(f"  filter kept all {len(unfiltered)}")


def _print_cor_form(base_url: str, form: str, *, en_query: str | None) -> None:
    variants = _fetch_cor_variants(base_url, form, en_query=en_query)
    if not variants:
        print("  (no variants)")
        return
    print(f"  {'cor_id':<22} {'lemma':<12} {'pos':<5} {'form':<10} gram")
    for variant in variants:
        gloss_suffix = f"   « {variant.get('gloss')}" if variant.get("gloss") else ""
        print(
            f"  {variant['cor_id']:<22} {variant['lemma']:<12} "
            f"{variant['pos_tag'] or '?':<5} {variant['form']:<10} {variant['gram_raw']}{gloss_suffix}"
        )


# ----------------------------------------------------------------------
# HTTP plumbing
# ----------------------------------------------------------------------


def _get_json(base_url: str, path: str, params: dict[str, str]) -> dict[str, Any] | None:
    url = f"{base_url}{path}?{urllib.parse.urlencode(params)}"
    label = _timing_label(path, params)
    start = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        elapsed = time.perf_counter() - start
        TIMINGS.append((f"{label} [HTTP {exc.code}]", elapsed))
        print(f"  HTTP {exc.code} on {url}: {exc.reason} ({elapsed * 1000:.0f} ms)", file=sys.stderr)
        try:
            body = exc.read().decode("utf-8", errors="replace")
            if body:
                print(f"  body: {body[:300]}", file=sys.stderr)
        except Exception:
            pass
        return None
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        elapsed = time.perf_counter() - start
        TIMINGS.append((f"{label} [error]", elapsed))
        print(f"  network error on {url}: {exc} ({elapsed * 1000:.0f} ms)", file=sys.stderr)
        return None
    elapsed = time.perf_counter() - start
    TIMINGS.append((label, elapsed))
    print(f"  · {label} → {elapsed * 1000:.0f} ms")
    return payload


def _timing_label(path: str, params: dict[str, str]) -> str:
    endpoint = path.rsplit("/", 1)[-1]
    form = params.get("form", "")
    en_query = params.get("en_query")
    en_pos = params.get("en_pos_ud")
    bits = [endpoint, form] if form else [endpoint]
    flags: list[str] = []
    if en_query:
        flags.append(f"en={en_query}")
    if en_pos:
        flags.append(f"pos={en_pos}")
    elif en_query is None and endpoint == "cor-form":
        flags.append("unfiltered")
    if flags:
        bits.append(f"[{', '.join(flags)}]")
    return " ".join(bits)


def _print_timings(start: float) -> None:
    total_ms = (time.perf_counter() - start) * 1000
    if not TIMINGS:
        print(f"\n[timing] total {total_ms:.0f} ms")
        return
    print("\n=== Timings ===")
    width = max(len(label) for label, _ in TIMINGS)
    sum_ms = 0.0
    for label, elapsed in TIMINGS:
        ms = elapsed * 1000
        sum_ms += ms
        print(f"  {label.ljust(width)}  {ms:7.0f} ms")
    print(f"  {'(sum HTTP)'.ljust(width)}  {sum_ms:7.0f} ms")
    print(f"  {'total wall'.ljust(width)}  {total_ms:7.0f} ms")


def _print_section(title: str) -> None:
    print(f"\n=== {title} ===")


if __name__ == "__main__":
    sys.exit(main())

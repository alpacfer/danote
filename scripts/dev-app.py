#!/usr/bin/env python3
"""JSON-only live API controller for Danote development debugging."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any

DEFAULT_HOSTS = ("127.0.0.1", "localhost")
DEFAULT_PORTS = (8000, 8001, 8002)
DEFAULT_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class RequestSpec:
    method: str
    path: str
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None


@dataclass(frozen=True)
class TargetSpec:
    kind: str
    meaning_id: int | None = None
    surface_form: str | None = None


class DevAppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: str | None = None,
        request: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.body = body
        self.request = request


class ApiClient:
    def __init__(self, base_url: str, *, timeout: float, token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token = token
        self.timings: list[dict[str, Any]] = []

    def request(self, spec: RequestSpec) -> Any:
        url = self._url(spec.path, spec.params)
        data = None
        headers = {"Accept": "application/json"}
        if spec.body is not None:
            data = json.dumps(spec.body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(url, data=data, headers=headers, method=spec.method)
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                payload = _decode_json(raw)
                elapsed_ms = (time.perf_counter() - start) * 1000
                self.timings.append(_timing(spec, elapsed_ms, status=response.status))
                return payload
        except urllib.error.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            body = exc.read().decode("utf-8", errors="replace")
            self.timings.append(_timing(spec, elapsed_ms, status=exc.code))
            raise DevAppError(
                f"HTTP {exc.code}: {exc.reason}",
                status=exc.code,
                body=body,
                request=request_payload(spec),
            ) from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.timings.append(_timing(spec, elapsed_ms, status=None))
            raise DevAppError(str(exc), request=request_payload(spec)) from exc

    def _url(self, path: str, params: dict[str, Any] | None) -> str:
        query = _query_string(params or {})
        suffix = f"?{query}" if query else ""
        return f"{self.base_url}{path}{suffix}"


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    command = " ".join(args.command_path)
    try:
        base_url = resolve_base_url(args)
        if base_url is None:
            raise DevAppError("Could not locate a running backend. Start `make dev` first, or pass --base-url.")
        token = args.token or os.environ.get("DANOTE_AUTH_TOKEN")
        client = ApiClient(base_url, timeout=args.timeout, token=token)
        result = args.handler(args, client)
        print_json(success_envelope(command, client, result))
        return 0
    except DevAppError as exc:
        print_json(error_envelope(command, args, exc))
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", help="Backend base URL, e.g. http://127.0.0.1:8000.")
    parser.add_argument("--host", help="Backend host for auto-built base URL.")
    parser.add_argument("--port", type=int, help="Backend port for auto-built base URL.")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS, help="HTTP timeout in seconds.")
    parser.add_argument("--token", help="Bearer token. Defaults to DANOTE_AUTH_TOKEN when set.")
    subparsers = parser.add_subparsers(dest="root_command", required=True)

    _add_health_parser(subparsers)
    _add_developer_parser(subparsers)
    _add_search_parser(subparsers)
    _add_wordbank_parser(subparsers)
    _add_sentencebank_parser(subparsers)
    return parser


def _add_health_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("health", help="Read backend health.")
    _set_handler(parser, ["health"], lambda _args, client: run_single(client, RequestSpec("GET", "/api/health")))


def _add_developer_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("developer", help="Developer actions.")
    child = parser.add_subparsers(dest="developer_command", required=True)
    probe = child.add_parser("probe", help="Run a developer probe.")
    probe.add_argument("provider", choices=("gemini", "translation", "tts"))
    _set_handler(probe, ["developer", "probe"], handle_developer_probe)
    reset = child.add_parser("reset-db", help="Delete and recreate the app database.")
    _set_handler(reset, ["developer", "reset-db"], lambda _args, client: run_single(client, RequestSpec("DELETE", "/api/wordbank/database")))


def _add_search_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("search", help="Search and resolver commands.")
    child = parser.add_subparsers(dest="search_command", required=True)

    resolve = child.add_parser("resolve", help="Resolve a sidebar query.")
    resolve.add_argument("query")
    _set_handler(resolve, ["search", "resolve"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/resolve-query", body={"query_text": args.query})))

    en = child.add_parser("en", help="Search local English dictionary form.")
    en.add_argument("form")
    en.add_argument("--include-translations", type=parse_bool, default=True)
    _set_handler(en, ["search", "en"], lambda args, client: run_single(client, RequestSpec("GET", "/api/wordbank/search/en-form", {"form": args.form, "include_translations": args.include_translations})))

    cor = child.add_parser("cor", help="Search COR form.")
    _add_cor_args(cor)
    _set_handler(cor, ["search", "cor"], handle_search_cor)

    lemma = child.add_parser("cor-lemma", help="Read COR lemma paradigm.")
    lemma.add_argument("lemma_idx", type=int)
    lemma.add_argument("--limit", type=int, default=1000)
    _set_handler(lemma, ["search", "cor-lemma"], lambda args, client: run_single(client, RequestSpec("GET", f"/api/wordbank/search/cor-lemma/{args.lemma_idx}", {"limit": args.limit})))

    trace = child.add_parser("trace", help="Structured EN to DA to COR trace.")
    trace.add_argument("query")
    _set_handler(trace, ["search", "trace"], handle_search_trace)

    profile = child.add_parser("profile", help="Profile sidebar-style single-word search.")
    profile.add_argument("query")
    profile.add_argument("--runs", type=int, default=1, help="Number of profile runs.")
    profile.add_argument("--cold-cache", action="store_true", help="Clear search cache before each run when enabled.")
    profile.add_argument("--include-resolve", action="store_true", help="Also time /api/wordbank/resolve-query.")
    profile.add_argument(
        "--legacy-cor-loop",
        action="store_true",
        help="Use one filtered COR GET per English translation instead of cor-form-batch.",
    )
    _set_handler(profile, ["search", "profile"], handle_search_profile)

    all_results = child.add_parser(
        "all",
        help="List every search result for a query plus typo suggestions.",
    )
    all_results.add_argument("query")
    all_results.add_argument("--limit", type=int, default=8, help="Wordbank result limit.")
    _set_handler(all_results, ["search", "all"], handle_search_all)


def _add_wordbank_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("wordbank", help="Wordbank commands.")
    child = parser.add_subparsers(dest="wordbank_command", required=True)

    list_parser = child.add_parser("list", help="List saved lemmas.")
    list_parser.add_argument("--pos-tag", "--pos", help="Filter lemmas by word type / POS tag (case-insensitive).")
    list_parser.add_argument("--category", "--cat", help="Filter lemmas by semantic category (case-insensitive).")
    _set_handler(list_parser, ["wordbank", "list"], handle_wordbank_list)

    details = child.add_parser("details", help="Read lemma details.")
    details.add_argument("lemma")
    details.add_argument(
        "--brief",
        action="store_true",
        help="Project a compact per-meaning view (id, key, en, gloss, gloss_translation, saved_id).",
    )
    _set_handler(details, ["wordbank", "details"], handle_wordbank_details)

    category_status = child.add_parser("category-status", help="Summarize lemma categories and verification statuses.")
    category_status.add_argument("lemma")
    category_status.add_argument("--polls", type=int, default=1, help="Number of detail snapshots to read.")
    category_status.add_argument("--interval", type=float, default=0.75, help="Seconds between snapshots.")
    category_status.add_argument(
        "--expect-category",
        action="append",
        default=[],
        help="Expected category label. May be repeated; exits non-zero if any are missing from the final snapshot.",
    )
    _set_handler(category_status, ["wordbank", "category-status"], handle_wordbank_category_status)

    search = child.add_parser("search", help="Search saved wordbank.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=8)
    _set_handler(search, ["wordbank", "search"], lambda args, client: run_single(client, RequestSpec("GET", "/api/wordbank/search", {"query": args.query, "limit": args.limit})))

    add = child.add_parser("add", help="Add a word.")
    add.add_argument("--surface", required=True)
    add.add_argument("--lemma")
    add.add_argument("--cor-id")
    add.add_argument("--pos-tag")
    add.add_argument("--morphology")
    add.add_argument("--search-seed-json")
    _set_handler(add, ["wordbank", "add"], handle_wordbank_add)

    delete_lemma = child.add_parser("delete-lemma", help="Delete a lemma immediately.")
    delete_lemma.add_argument("lemma")
    _set_handler(delete_lemma, ["wordbank", "delete-lemma"], lambda args, client: run_single(client, RequestSpec("DELETE", f"/api/wordbank/lemmas/{quote_path(args.lemma)}")))

    delete_meaning = child.add_parser("delete-meaning", help="Delete a meaning immediately.")
    delete_meaning.add_argument("meaning_id", type=int)
    _set_handler(delete_meaning, ["wordbank", "delete-meaning"], lambda args, client: run_single(client, RequestSpec("DELETE", f"/api/wordbank/meanings/{args.meaning_id}")))

    save_sense = child.add_parser(
        "save-sense",
        help="Save one discovered sense by meaning_key, auto-building the search seed.",
    )
    save_sense.add_argument("surface", help="Surface form to look up (e.g. 'holder', 'slår', 'kort').")
    save_sense.add_argument("--meaning-key", required=True, help="meaning_key of the sense to save (from sense-discovery output).")
    save_sense.add_argument("--lemma", help="Override the discovered lemma; defaults to the variant's COR lemma.")
    save_sense.add_argument("--pos-tag", help="Restrict matching to variants of this POS (NOUN/VERB/ADJ/ADV).")
    _set_handler(save_sense, ["wordbank", "save-sense"], handle_wordbank_save_sense)

    expand = child.add_parser(
        "expand-senses",
        help="Backfill discovered senses for an already-saved lemma (idempotent).",
    )
    expand.add_argument("lemma")
    _set_handler(
        expand,
        ["wordbank", "expand-senses"],
        lambda args, client: run_single(
            client,
            RequestSpec("POST", "/api/wordbank/lexemes/expand-senses", body={"lemma": args.lemma}),
        ),
    )

    sense_discovery = child.add_parser(
        "sense-discovery",
        help="Inspect raw Gemini sense-discovery output for the lemma behind a surface form.",
    )
    sense_discovery.add_argument("form", help="Surface form (lemma resolution done backend-side).")
    _set_handler(sense_discovery, ["wordbank", "sense-discovery"], handle_wordbank_sense_discovery)

    _add_wordbank_action_parsers(child)
    _add_verification_parsers(child)


def _add_wordbank_action_parsers(child: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    complete = child.add_parser("complete-variations", help="Complete meaning variations.")
    complete.add_argument("lemma")
    complete.add_argument("--meaning-id", type=int, required=True)
    _set_handler(complete, ["wordbank", "complete-variations"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/complete-variations", body={"stored_lemma": args.lemma, "meaning_id": args.meaning_id})))

    pronunciation = child.add_parser("pronunciation", help="Generate or regenerate word pronunciation.")
    pronunciation.add_argument("lemma")
    pronunciation.add_argument("--surface")
    pronunciation.add_argument("--force", action="store_true")
    _set_handler(pronunciation, ["wordbank", "pronunciation"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/pronunciation", body={"stored_lemma": args.lemma, "stored_surface_form": args.surface, "force": args.force})))

    rethink = child.add_parser("rethink-categories", help="Rerun category classification.")
    _add_target_scope_args(rethink)
    _set_handler(rethink, ["wordbank", "rethink-categories"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/rethink-categories", body=scope_body(args))))

    alternatives = child.add_parser("alternative-translations", help="Find alternative translations.")
    alternatives.add_argument("lemma")
    alternatives.add_argument("--meaning-id", type=int)
    _set_handler(alternatives, ["wordbank", "alternative-translations"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/find-alternative-translations", body={"stored_lemma": args.lemma, "meaning_id": args.meaning_id})))


def _add_verification_parsers(child: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    verify = child.add_parser("verify", help="Run verification now.")
    _add_target_scope_args(verify)
    _set_handler(verify, ["wordbank", "verify"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/verify", body=scope_body(args))))

    queue = child.add_parser("queue-verification", help="Queue verification.")
    _add_target_scope_args(queue)
    queue.add_argument("--review-intent", default="general")
    _set_handler(queue, ["wordbank", "queue-verification"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/queue-verification", body={**scope_body(args), "review_intent": args.review_intent})))

    overview = child.add_parser("verification", help="Read normalized verification targets.")
    overview.add_argument("lemma")
    _set_handler(overview, ["wordbank", "verification"], handle_verification_overview)

    apply = child.add_parser("apply-action", help="Apply a suggested verification action.")
    apply.add_argument("lemma")
    apply.add_argument("--target", required=True, help="lemma, meaning:ID, or surface:ID:FORM. Use root for no meaning id.")
    apply.add_argument("--action-index", type=int, required=True)
    _set_handler(apply, ["wordbank", "apply-action"], handle_apply_action)

    changes = child.add_parser("verification-changes", help="Read verification change log.")
    changes.add_argument("lemma")
    _set_handler(changes, ["wordbank", "verification-changes"], lambda args, client: run_single(client, RequestSpec("GET", "/api/wordbank/lexemes/verification-changes", {"stored_lemma": args.lemma})))

    revert = child.add_parser("revert-verification-change", help="Revert a logged verification change.")
    revert.add_argument("lemma")
    revert.add_argument("--change-id", type=int, required=True)
    _set_handler(revert, ["wordbank", "revert-verification-change"], lambda args, client: run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/revert-verification-change", body={"stored_lemma": args.lemma, "change_id": args.change_id})))


def _add_sentencebank_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("sentencebank", help="Sentencebank commands.")
    child = parser.add_subparsers(dest="sentencebank_command", required=True)

    _set_handler(child.add_parser("list", help="List sentences."), ["sentencebank", "list"], lambda _args, client: run_single(client, RequestSpec("GET", "/api/sentencebank/sentences")))

    preview = child.add_parser("preview", help="Preview sentence search/save.")
    preview.add_argument("text")
    preview.add_argument("--fast", action="store_true")
    _set_handler(preview, ["sentencebank", "preview"], lambda args, client: run_single(client, RequestSpec("POST", "/api/sentencebank/search-preview", body={"source_text": args.text, "fast": args.fast})))

    add = child.add_parser("add", help="Add a sentence.")
    add.add_argument("text")
    add.add_argument("--english-translation")
    add.add_argument("--token-persistence-mode", choices=("auto_save_all", "link_existing_only"), default="auto_save_all")
    add.add_argument("--target-json")
    _set_handler(add, ["sentencebank", "add"], handle_sentencebank_add)

    save = child.add_parser("save-token", help="Save one unsaved sentence token.")
    save.add_argument("sentence_id", type=int)
    save.add_argument("token_index", type=int)
    _set_handler(save, ["sentencebank", "save-token"], lambda args, client: run_single(client, RequestSpec("POST", f"/api/sentencebank/sentences/{args.sentence_id}/tokens/{args.token_index}/save")))

    verify = child.add_parser("verify", help="Verify sentence text.")
    verify.add_argument("text")
    _set_handler(verify, ["sentencebank", "verify"], lambda args, client: run_single(client, RequestSpec("POST", "/api/sentencebank/verify-sentence", body={"source_text": args.text})))

    pronunciation = child.add_parser("pronunciation", help="Generate sentence pronunciation.")
    pronunciation.add_argument("sentence_id", type=int)
    pronunciation.add_argument("--force", action="store_true")
    _set_handler(pronunciation, ["sentencebank", "pronunciation"], lambda args, client: run_single(client, RequestSpec("POST", "/api/sentencebank/sentences/pronunciation", body={"sentence_id": args.sentence_id, "force": args.force})))

    delete = child.add_parser("delete", help="Delete a sentence immediately.")
    delete.add_argument("sentence_id", type=int)
    delete.add_argument("--delete-meanings", action="store_true")
    _set_handler(delete, ["sentencebank", "delete"], lambda args, client: run_single(client, RequestSpec("DELETE", f"/api/sentencebank/sentences/{args.sentence_id}", {"delete_meanings": args.delete_meanings})))


def _add_cor_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("form")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--include-translations", type=parse_bool, default=True)
    parser.add_argument("--en-query")
    parser.add_argument("--en-pos-ud")


def _add_target_scope_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("lemma")
    parser.add_argument("--meaning-id", type=int)
    parser.add_argument("--surface")


def _set_handler(parser: argparse.ArgumentParser, command_path: list[str], handler: Any) -> None:
    parser.set_defaults(handler=handler, command_path=command_path)


def handle_developer_probe(args: argparse.Namespace, client: ApiClient) -> Any:
    paths = {
        "gemini": "/api/developer/gemini-probe",
        "translation": "/api/developer/translation-probe",
        "tts": "/api/developer/tts-probe",
    }
    return run_single(client, RequestSpec("POST", paths[args.provider]))


def handle_search_cor(args: argparse.Namespace, client: ApiClient) -> Any:
    return run_single(client, RequestSpec("GET", "/api/wordbank/search/cor-form", cor_params(args)))


def handle_search_profile(args: argparse.Namespace, client: ApiClient) -> dict[str, Any]:
    runs = max(1, args.runs)
    query = args.query
    normalized_query = normalize_search_word(query)
    decision = search_flow_decision(normalized_query)
    results = []
    for run_index in range(runs):
        if args.cold_cache:
            clear_search_cache(client)
        results.append(
            run_search_profile_once(
                client,
                query=query,
                normalized_query=normalized_query,
                decision=decision,
                run_index=run_index,
                cold_cache=args.cold_cache,
                include_resolve=args.include_resolve,
                use_cor_batch=not args.legacy_cor_loop,
            )
        )
    return {
        "query": query,
        "normalized_query": normalized_query,
        "decision": decision,
        "runs": results,
        "summary": summarize_profile_runs(results),
    }


def handle_search_all(args: argparse.Namespace, client: ApiClient) -> dict[str, Any]:
    query = args.query
    wordbank = client.request(
        RequestSpec("GET", "/api/wordbank/search", {"query": query, "limit": args.limit})
    )
    cor_form = client.request(
        RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            {"form": query, "limit": 100, "include_translations": True},
        )
    )
    en_form = client.request(
        RequestSpec(
            "GET",
            "/api/wordbank/search/en-form",
            {"form": query, "include_translations": True},
        )
    )
    resolve = client.request(
        RequestSpec("POST", "/api/wordbank/resolve-query", body={"query_text": query})
    )

    saved_results = [
        {
            "lemma": item.get("lemma"),
            "display_lemma": item.get("display_lemma"),
            "meaning_id": item.get("meaning_id"),
            "meaning_key": item.get("meaning_key"),
            "match_surface": item.get("match_surface"),
            "english_translation": item.get("english_translation"),
            "pos_tag": item.get("pos_tag"),
            "cor_lemma_idx": item.get("cor_lemma_idx"),
            "query_cor_ids": item.get("query_cor_ids") or [],
            "variation_count": item.get("variation_count"),
        }
        for item in (wordbank.get("items") or [])
    ]
    cor_results = [
        {
            "cor_id": variant.get("cor_id"),
            "form": variant.get("form"),
            "lemma": variant.get("lemma"),
            "lemma_idx": variant.get("lemma_idx"),
            "pos_tag": variant.get("pos_tag") or group.get("pos_tag"),
            "gloss": variant.get("gloss") or group.get("gloss"),
            "lemma_translation": variant.get("lemma_translation"),
            "saveable_translation": variant.get("saveable_translation"),
            "gram_raw": variant.get("gram_raw"),
            "dictionary_status": variant.get("dictionary_status"),
            "meaning_key": variant.get("meaning_key"),
            "english_gloss": variant.get("english_gloss"),
            "saved_meaning_id": variant.get("saved_meaning_id"),
            "alternative_translations": variant.get("alternative_translations") or [],
            "example_da": variant.get("example_da"),
            "example_en": variant.get("example_en"),
        }
        for group in (cor_form.get("groups") or [])
        for variant in (group.get("variants") or [])
    ]
    en_results = [
        {
            "lemma": group.get("lemma"),
            "form": group.get("form"),
            "pos_ud": group.get("pos_ud"),
            "pos_raw": group.get("pos_raw"),
            "danish_translation": group.get("danish_translation"),
            "meaning_description": group.get("meaning_description"),
            "sense_count": len(group.get("senses") or []),
        }
        for group in (en_form.get("groups") or [])
    ]
    word_actions = resolve.get("word_actions") or []

    return {
        "query": query,
        "summary": {
            "saved_wordbank": len(saved_results),
            "cor_variants": len(cor_results),
            "en_results": len(en_results),
            "word_actions": len(word_actions),
        },
        "typo_suggestions": {
            "wordbank": wordbank.get("did_you_mean"),
            "cor_form": cor_form.get("did_you_mean"),
        },
        "saved_wordbank_results": saved_results,
        "cor_results": cor_results,
        "en_results": en_results,
        "resolver": {
            "classification": resolve.get("classification"),
            "query_language": resolve.get("query_language"),
            "resolved_lemma": resolve.get("resolved_lemma"),
            "matched_lemma": resolve.get("matched_lemma"),
            "word_actions": word_actions,
        },
    }


def handle_search_trace(args: argparse.Namespace, client: ApiClient) -> dict[str, Any]:
    en_payload = client.request(RequestSpec("GET", "/api/wordbank/search/en-form", {"form": args.query}))
    groups = en_payload.get("groups") or []
    trace_items = []
    for key, label, pos_values in translation_keys(groups):
        pos_param = ",".join(sorted(pos_values)) if pos_values else None
        base_params = {"form": label, "limit": 100, "include_translations": False}
        filtered_params = {**base_params, "en_query": args.query}
        if pos_param:
            filtered_params["en_pos_ud"] = pos_param
        unfiltered = client.request(RequestSpec("GET", "/api/wordbank/search/cor-form", base_params))
        filtered = client.request(RequestSpec("GET", "/api/wordbank/search/cor-form", filtered_params))
        trace_items.append(
            {
                "translation_key": key,
                "danish_translation": label,
                "en_pos_ud": sorted(pos_values),
                "unfiltered": flatten_cor_variants(unfiltered),
                "filtered": flatten_cor_variants(filtered),
                "diff": diff_cor_variants(unfiltered, filtered),
            }
        )
    return {"query": args.query, "en": en_payload, "cor_traces": trace_items}


def run_search_profile_once(
    client: ApiClient,
    *,
    query: str,
    normalized_query: str,
    decision: dict[str, Any],
    run_index: int,
    cold_cache: bool,
    include_resolve: bool,
    use_cor_batch: bool,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    phases: list[dict[str, Any]] = []
    responses: dict[str, Any] = {}

    if decision["skip_word_lookups"]:
        return {
            "run_index": run_index,
            "cold_cache": cold_cache,
            "total_wall_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "phases": phases,
            "counts": {},
            "flow": {"skipped": True, "skip_reason": decision["skip_reason"]},
        }

    initial_specs = {
        "wordbank": RequestSpec("GET", "/api/wordbank/search", {"query": normalized_query, "limit": 8}),
        "cor_partial": RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            {"form": normalized_query, "limit": 100, "include_translations": False},
        ),
        "en_form": RequestSpec(
            "GET",
            "/api/wordbank/search/en-form",
            {"form": normalized_query, "include_translations": True},
        ),
    }
    initial = run_profile_requests(client, initial_specs)
    for name in ("wordbank", "cor_partial", "en_form"):
        record_profile_phase(phases, name, initial[name])
        responses[name] = initial[name].get("response")

    translation_items = profile_translation_items(query, responses.get("en_form") or {})
    translated_cor_payloads: dict[str, Any] = {}
    skip_direct_full = should_skip_direct_cor_full(
        responses.get("cor_partial") or {},
        normalized_query,
        responses.get("en_form") or {},
    )
    with ThreadPoolExecutor(max_workers=2) as executor:
        direct_full_future = None
        if not skip_direct_full:
            direct_full_future = executor.submit(
                run_profile_request,
                client,
                RequestSpec(
                    "GET",
                    "/api/wordbank/search/cor-form",
                    {"form": normalized_query, "limit": 100, "include_translations": True},
                ),
            )
        translated_future = executor.submit(
            run_en_translated_cor_profile,
            client,
            translation_items=translation_items,
            use_cor_batch=use_cor_batch,
        )
        direct_full_result = direct_full_future.result() if direct_full_future is not None else None
        translated_result = translated_future.result()

    if direct_full_result is not None:
        record_profile_phase(phases, "cor_full", direct_full_result)
        responses["cor_full"] = direct_full_result.get("response")
    for phase in translated_result["phases"]:
        phases.append(phase)
    translated_cor_payloads = translated_result["payloads"]

    if include_resolve:
        resolve_result = run_profile_request(
            client,
            RequestSpec("POST", "/api/wordbank/resolve-query", body={"query_text": query}),
        )
        record_profile_phase(phases, "resolve", resolve_result)
        responses["resolve"] = resolve_result.get("response")

    total_wall_ms = round((time.perf_counter() - started_at) * 1000, 3)
    return {
        "run_index": run_index,
        "cold_cache": cold_cache,
        "total_wall_ms": total_wall_ms,
        "phases": phases,
        "counts": profile_counts(responses, translated_cor_payloads),
        "flow": {
            "skipped": False,
            "translation_keys": translation_items,
            "used_cor_batch": use_cor_batch,
            "included_resolve": include_resolve,
            "skipped_direct_cor_full": skip_direct_full,
        },
    }


def run_en_translated_cor_profile(
    client: ApiClient,
    *,
    translation_items: list[dict[str, str | None]],
    use_cor_batch: bool,
) -> dict[str, Any]:
    phases: list[dict[str, Any]] = []
    payloads: dict[str, Any] = {}
    if not translation_items:
        return {"phases": phases, "payloads": payloads}

    partial_specs = {
        f"en_cor_partial:{item['form']}": RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            {"form": item["form"], "limit": 100, "include_translations": False},
        )
        for item in translation_items
    }
    partials = run_profile_requests(client, partial_specs)
    for name, result in partials.items():
        record_profile_phase(phases, name, result)

    if use_cor_batch:
        batch_result = run_profile_request(
            client,
            RequestSpec(
                "POST",
                "/api/wordbank/search/cor-form-batch",
                body={
                    "limit": 100,
                    "include_translations": True,
                    "items": translation_items,
                },
            ),
        )
        record_profile_phase(phases, "en_cor_batch", batch_result)
        batch_payload = batch_result.get("response") or {}
        for item, payload in zip(translation_items, batch_payload.get("items") or []):
            payloads[str(item["form"])] = payload
        return {"phases": phases, "payloads": payloads}

    filtered_specs = {}
    for item in translation_items:
        params = {
            "form": item["form"],
            "limit": 100,
            "include_translations": True,
            "en_query": item["en_query"],
            "en_pos_ud": item.get("en_pos_ud"),
        }
        filtered_specs[f"en_cor_filtered:{item['form']}"] = RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            params,
        )
    filtered = run_profile_requests(client, filtered_specs)
    for name, result in filtered.items():
        record_profile_phase(phases, name, result)
        form = name.split(":", 1)[1]
        payloads[form] = result.get("response")
    return {"phases": phases, "payloads": payloads}


def run_profile_requests(client: ApiClient, specs: dict[str, RequestSpec]) -> dict[str, dict[str, Any]]:
    if not specs:
        return {}
    results: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(specs))) as executor:
        futures = {
            executor.submit(run_profile_request, client, spec): name
            for name, spec in specs.items()
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


def run_profile_request(client: ApiClient, spec: RequestSpec) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        response = client.request(spec)
    except DevAppError as exc:
        return {
            "ok": False,
            "status": exc.status,
            "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 3),
            "request": request_payload(spec),
            "error": str(exc),
            "body": exc.body,
        }
    return {
        "ok": True,
        "status": 200,
        "elapsed_ms": round((time.perf_counter() - started_at) * 1000, 3),
        "request": request_payload(spec),
        "response": response,
    }


def record_profile_phase(phases: list[dict[str, Any]], name: str, result: dict[str, Any]) -> None:
    phase = {
        "name": name,
        "ok": result["ok"],
        "status": result.get("status"),
        "elapsed_ms": result["elapsed_ms"],
        "request": result["request"],
    }
    if not result["ok"]:
        phase["error"] = result.get("error")
    phases.append(phase)


def profile_translation_items(query: str, en_payload: dict[str, Any]) -> list[dict[str, str | None]]:
    return [
        {
            "form": label,
            "en_query": query,
            "en_pos_ud": ",".join(sorted(pos_values)) or None,
        }
        for _key, label, pos_values in translation_keys(en_payload.get("groups") or [])
    ]


def profile_counts(responses: dict[str, Any], translated_cor_payloads: dict[str, Any]) -> dict[str, int]:
    return {
        "wordbank_items": len((responses.get("wordbank") or {}).get("items") or []),
        "direct_cor_partial_variants": count_cor_variants(responses.get("cor_partial") or {}),
        "direct_cor_full_variants": count_cor_variants(responses.get("cor_full") or {}),
        "en_groups": len((responses.get("en_form") or {}).get("groups") or []),
        "translated_cor_forms": len(translated_cor_payloads),
        "translated_cor_variants": sum(count_cor_variants(payload or {}) for payload in translated_cor_payloads.values()),
        "resolve_actions": len((responses.get("resolve") or {}).get("word_actions") or []),
    }


def count_cor_variants(payload: dict[str, Any]) -> int:
    return sum(len(group.get("variants") or []) for group in payload.get("groups") or [])


def should_skip_direct_cor_full(
    partial_payload: dict[str, Any],
    normalized_query: str,
    en_payload: dict[str, Any],
) -> bool:
    if not (en_payload.get("groups") or []):
        return False
    groups = partial_payload.get("groups") or []
    if not groups:
        return True
    for group in groups:
        if str(group.get("gloss") or "").strip():
            return False
        if str(group.get("pos_tag") or "").strip().upper() != "VERB":
            return False
        variants = group.get("variants") or []
        if not variants:
            return False
        for variant in variants:
            form = str(variant.get("form") or "").strip().lower()
            lemma = str(variant.get("lemma") or "").strip().lower()
            gloss = str(variant.get("gloss") or "").strip()
            if form != normalized_query or lemma == normalized_query or gloss:
                return False
    return True


def summarize_profile_runs(runs: list[dict[str, Any]]) -> dict[str, Any]:
    if not runs:
        return {}
    totals = [float(run.get("total_wall_ms") or 0.0) for run in runs]
    phase_totals: dict[str, list[float]] = {}
    for run in runs:
        for phase in run.get("phases") or []:
            phase_totals.setdefault(str(phase.get("name") or ""), []).append(float(phase.get("elapsed_ms") or 0.0))
    return {
        "runs": len(runs),
        "p50_wall_ms": percentile(totals, 0.5),
        "p95_wall_ms": percentile(totals, 0.95),
        "phases_p50_ms": {
            name: percentile(values, 0.5)
            for name, values in sorted(phase_totals.items())
            if name
        },
    }


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return round(ordered[index], 3)


def search_flow_decision(normalized_query: str) -> dict[str, Any]:
    number_mode = is_number_query(normalized_query)
    sentence_mode = not number_mode and has_multiple_words(normalized_query)
    short_word = is_short_letter_word(normalized_query)
    skip_reason = None
    if number_mode:
        skip_reason = "number_mode"
    elif sentence_mode:
        skip_reason = "sentence_mode"
    elif not normalized_query:
        skip_reason = "empty_query"
    elif len(normalized_query) < 2:
        skip_reason = "too_short"
    elif short_word:
        skip_reason = "short_letter_word"
    return {
        "number_mode": number_mode,
        "sentence_mode": sentence_mode,
        "short_letter_word": short_word,
        "single_word_lookup": skip_reason is None,
        "skip_word_lookups": skip_reason is not None,
        "skip_reason": skip_reason,
    }


def normalize_search_word(value: str) -> str:
    return " ".join(value.strip().lower().split())


def has_multiple_words(value: str) -> bool:
    return len([part for part in value.split() if part]) >= 2


def is_number_query(value: str) -> bool:
    cleaned = value.replace(".", "").replace(",", "").replace(" ", "")
    return bool(cleaned) and cleaned.isdigit()


def is_short_letter_word(value: str) -> bool:
    return value.isalpha() and len(value) <= 2


def clear_search_cache(client: ApiClient) -> None:
    try:
        client.request(RequestSpec("POST", "/api/admin/clear-search-cache", body={}))
    except DevAppError:
        return


UD_POS_PRIMARY_LABELS = {
    "ADJ": "Adjective",
    "ADP": "Preposition",
    "ADV": "Adverb",
    "AUX": "Auxiliary",
    "CCONJ": "Conjunction",
    "DET": "Determiner",
    "INTJ": "Interjection",
    "NOUN": "Noun",
    "NUM": "Numeral",
    "PART": "Particle",
    "PRON": "Pronoun",
    "PROPN": "Proper noun",
    "PUNCT": "Punctuation",
    "SCONJ": "Subordinating conjunction",
    "SYM": "Symbol",
    "VERB": "Verb",
    "X": "Other",
    "PHRASAL_VERB": "Phrasal verb",
    "IDIOM": "Idiom",
}


def is_multi_word_lemma(lemma: str | None) -> bool:
    return bool(lemma and " " in lemma.strip())


def primary_pos_label_for_lemma(pos_tag: str | None, lemma: str | None) -> str | None:
    if is_multi_word_lemma(lemma):
        upper = (pos_tag or "").strip().upper().replace(" ", "_").replace("-", "_")
        if upper in {"VERB", "AUX", "PHRASAL_VERB", "MWE"}:
            return "Phrasal verb"
        return "Idiom"
    return primary_pos_label(pos_tag)


def primary_pos_label(pos_tag: str | None) -> str | None:
    if not pos_tag:
        return None
    upper = pos_tag.strip().upper()
    return UD_POS_PRIMARY_LABELS.get(upper, pos_tag)


def handle_wordbank_list(args: argparse.Namespace, client: ApiClient) -> Any:
    payload = client.request(RequestSpec("GET", "/api/wordbank/lemmas"))
    items = payload.get("items") or []

    if args.pos_tag:
        target_pos = args.pos_tag.strip().lower().replace("_", " ")
        filtered_items = []
        for item in items:
            pos_tags = item.get("pos_tags") or []
            lemma = item.get("lemma")
            is_mwe = is_multi_word_lemma(lemma)
            upper_tags = [t.strip().upper() for t in pos_tags if t.strip()]
            has_verb = any(t in {"VERB", "AUX"} for t in upper_tags)

            matched = False
            if target_pos in {"phrasal verb", "phrasal_verb"}:
                matched = is_mwe and has_verb
            elif target_pos == "idiom":
                matched = is_mwe and not has_verb
            else:
                for pos in pos_tags:
                    pos = pos.strip()
                    if pos.lower() == target_pos:
                        matched = True
                        break
                    label = primary_pos_label_for_lemma(pos, lemma)
                    if label and label.lower() == target_pos:
                        matched = True
                        break
            if matched:
                filtered_items.append(item)
        items = filtered_items

    if args.category:
        target_cat = args.category.strip().lower()
        items = [
            item for item in items
            if any(cat.strip().lower() == target_cat for cat in (item.get("categories") or []))
        ]

    payload["items"] = items
    return payload


def handle_wordbank_category_status(args: argparse.Namespace, client: ApiClient) -> dict[str, Any]:
    polls = max(1, args.polls)
    interval = max(0.0, args.interval)
    snapshots = []
    for poll_index in range(polls):
        if poll_index > 0 and interval:
            time.sleep(interval)
        details = get_lemma_details(client, args.lemma)
        snapshots.append(category_status_snapshot(details, poll_index=poll_index))

    final_categories = {
        normalize_category_label(category)
        for scope in snapshots[-1]["scopes"]
        for category in scope["categories"]
    }
    missing_expected = [
        label for label in args.expect_category
        if normalize_category_label(label) not in final_categories
    ]
    if missing_expected:
        raise DevAppError(
            f"Missing expected categories in final snapshot: {', '.join(missing_expected)}",
            request=client.timings[-1]["request"] if client.timings else None,
        )

    return {
        "lemma": snapshots[-1]["lemma"],
        "polls": polls,
        "interval_seconds": interval,
        "expected_categories": args.expect_category,
        "snapshots": snapshots,
        "final": snapshots[-1],
    }


def category_status_snapshot(details: dict[str, Any], *, poll_index: int) -> dict[str, Any]:
    scopes = collect_category_scopes(details)
    return {
        "poll_index": poll_index,
        "lemma": details.get("lemma"),
        "scope_count": len(scopes),
        "category_count": sum(len(scope["categories"]) for scope in scopes),
        "queued_verification_count": sum(1 for scope in scopes if scope.get("verification_status") == "queued"),
        "scopes": scopes,
    }


def collect_category_scopes(details: dict[str, Any]) -> list[dict[str, Any]]:
    lemma = str(details.get("lemma") or "")
    scopes = [
        category_scope_payload(
            kind="lemma",
            label=lemma,
            meaning_id=None,
            stored_surface_form=None,
            categories=details.get("categories") or [],
            verification=details.get("verification"),
        )
    ]
    for section in details.get("meaning_sections") or []:
        meaning_id = section.get("id")
        label = section.get("english_translation") or section.get("gloss") or section.get("meaning_key") or lemma
        scopes.append(
            category_scope_payload(
                kind="meaning",
                label=str(label),
                meaning_id=meaning_id,
                stored_surface_form=None,
                categories=section.get("categories") or [],
                verification=section.get("verification"),
            )
        )
        for form in section.get("surface_forms") or []:
            scopes.append(
                category_scope_payload(
                    kind="surface",
                    label=str(form.get("form") or ""),
                    meaning_id=meaning_id,
                    stored_surface_form=form.get("form"),
                    categories=[],
                    verification=form.get("verification"),
                )
            )
    if not details.get("meaning_sections"):
        for form in details.get("surface_forms") or []:
            scopes.append(
                category_scope_payload(
                    kind="surface",
                    label=str(form.get("form") or ""),
                    meaning_id=None,
                    stored_surface_form=form.get("form"),
                    categories=[],
                    verification=form.get("verification"),
                )
            )
    return scopes


def category_scope_payload(
    *,
    kind: str,
    label: str,
    meaning_id: int | None,
    stored_surface_form: str | None,
    categories: list[str],
    verification: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "label": label,
        "meaning_id": meaning_id,
        "stored_surface_form": stored_surface_form,
        "categories": categories,
        "verification_status": (verification or {}).get("status"),
        "verification_completed_at": (verification or {}).get("completed_at"),
    }


def normalize_category_label(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())



def handle_wordbank_add(args: argparse.Namespace, client: ApiClient) -> Any:
    body: dict[str, Any] = {
        "surface_token": args.surface,
        "lemma_candidate": args.lemma,
    }
    for arg_name, field_name in (("cor_id", "cor_id"), ("pos_tag", "pos_tag"), ("morphology", "morphology")):
        value = getattr(args, arg_name)
        if value:
            body[field_name] = value
    if args.search_seed_json:
        body["search_seed"] = parse_json_arg(args.search_seed_json, "--search-seed-json")
    return run_single(client, RequestSpec("POST", "/api/wordbank/lexemes", body=body))


def handle_wordbank_save_sense(args: argparse.Namespace, client: ApiClient) -> Any:
    """Convenience: run sense discovery for ``args.surface``, pick the variant
    whose ``meaning_key`` matches ``args.meaning_key``, build the full search
    seed (cor_id, cor_lemma_idx, gloss, english_gloss, english_translation,
    pos_tag, morphology) automatically, and POST add-word. Saves the 20-line
    raw curl I kept writing by hand to verify the per-sense save flow.
    """
    cor_form = client.request(
        RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            {"form": args.surface, "limit": 100, "include_translations": True},
        )
    )
    requested_pos = (args.pos_tag or "").strip().upper() or None
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for group in cor_form.get("groups") or []:
        for variant in group.get("variants") or []:
            if (variant.get("meaning_key") or "").strip().lower() != args.meaning_key.strip().lower():
                continue
            variant_pos = (variant.get("pos_tag") or group.get("pos_tag") or "").strip().upper() or None
            if requested_pos and variant_pos != requested_pos:
                continue
            matches.append((group, variant))
    if not matches:
        keys = sorted({
            f"{(v.get('meaning_key') or '?')}/{(v.get('pos_tag') or g.get('pos_tag') or '?')}"
            for g in (cor_form.get("groups") or [])
            for v in (g.get("variants") or [])
        })
        raise SystemExit(
            f"No sense matched meaning_key={args.meaning_key!r}"
            + (f" pos={requested_pos}" if requested_pos else "")
            + f". Available senses for {args.surface!r}: {', '.join(keys) or '(none)'}"
        )
    if len(matches) > 1:
        keys = sorted({
            f"{(v.get('meaning_key') or '?')}/{(v.get('pos_tag') or g.get('pos_tag') or '?')}"
            for g, v in matches
        })
        raise SystemExit(
            f"meaning_key={args.meaning_key!r} matched {len(matches)} variants ({', '.join(keys)}). "
            "Pass --pos-tag to disambiguate."
        )
    group, variant = matches[0]
    lemma = args.lemma or variant.get("lemma") or group.get("lemma")
    if not lemma:
        raise SystemExit("Variant does not expose a lemma; pass --lemma explicitly.")
    pos_tag = variant.get("pos_tag") or group.get("pos_tag")
    seed: dict[str, Any] = {
        "lemma": lemma,
        "surface": args.surface,
        "cor_id": variant.get("cor_id"),
        "cor_lemma_idx": variant.get("lemma_idx"),
        "dictionary_status": variant.get("dictionary_status") or "cor",
        "meaning_key": variant.get("meaning_key"),
        "gloss": variant.get("gloss") or group.get("gloss"),
        "english_gloss": variant.get("english_gloss"),
        "english_translation": variant.get("saveable_translation") or variant.get("lemma_translation"),
        "pos_tag": pos_tag,
        "morphology": variant.get("morphology"),
    }
    body: dict[str, Any] = {
        "surface_token": args.surface,
        "lemma_candidate": lemma,
        "cor_id": variant.get("cor_id"),
        "pos_tag": pos_tag,
        "morphology": variant.get("morphology"),
        "search_seed": seed,
    }
    return run_single(client, RequestSpec("POST", "/api/wordbank/lexemes", body=body))


def handle_wordbank_sense_discovery(args: argparse.Namespace, client: ApiClient) -> Any:
    """Project just the discovered-sense fields out of the cor-form fan-out so
    you can eyeball Gemini's output without the COR/translation noise."""
    cor_form = client.request(
        RequestSpec(
            "GET",
            "/api/wordbank/search/cor-form",
            {"form": args.form, "limit": 100, "include_translations": True},
        )
    )
    senses_by_lemma: dict[str, list[dict[str, Any]]] = {}
    for group in cor_form.get("groups") or []:
        lemma = group.get("lemma") or "?"
        for variant in group.get("variants") or []:
            if not variant.get("meaning_key"):
                continue
            senses_by_lemma.setdefault(lemma, []).append(
                {
                    "meaning_key": variant.get("meaning_key"),
                    "pos_tag": variant.get("pos_tag") or group.get("pos_tag"),
                    "english_translation": variant.get("saveable_translation"),
                    "english_gloss": variant.get("english_gloss"),
                    "gloss_da": variant.get("gloss") or group.get("gloss"),
                    "alternative_translations": variant.get("alternative_translations") or [],
                    "example_da": variant.get("example_da"),
                    "example_en": variant.get("example_en"),
                    "cor_id": variant.get("cor_id"),
                    "cor_lemma_idx": variant.get("lemma_idx"),
                }
            )
    return {
        "form": cor_form.get("form"),
        "did_you_mean": cor_form.get("did_you_mean"),
        "senses_by_lemma": senses_by_lemma,
        "sense_count": sum(len(v) for v in senses_by_lemma.values()),
    }


def handle_wordbank_details(args: argparse.Namespace, client: ApiClient) -> Any:
    details = get_lemma_details(client, args.lemma)
    if not args.brief:
        return details
    return _brief_lemma_details(details)


def _brief_lemma_details(details: dict[str, Any]) -> dict[str, Any]:
    sections = []
    for section in details.get("meaning_sections") or []:
        verification = section.get("verification") or {}
        sections.append(
            {
                "id": section.get("id"),
                "meaning_key": section.get("meaning_key"),
                "english_translation": section.get("english_translation"),
                # The resolved English parenthetical (computed from the row's
                # saved english_gloss when present, else translated via COR).
                # This is what the wordbank header renders after the lemma.
                "gloss_translation": section.get("gloss_translation"),
                "gloss_da": section.get("gloss"),
                "pos_tag": section.get("pos_tag"),
                "additional_translations": section.get("additional_translations") or [],
                "surface_forms": [form.get("form") for form in (section.get("surface_forms") or [])],
                "verification_status": verification.get("status"),
            }
        )
    return {
        "lemma": details.get("lemma"),
        "pos_tag": details.get("pos_tag"),
        "is_sectioned": details.get("is_sectioned"),
        "english_translation": details.get("english_translation"),
        "meaning_sections": sections,
        "top_level_surface_forms": [form.get("form") for form in (details.get("surface_forms") or [])],
    }


def handle_sentencebank_add(args: argparse.Namespace, client: ApiClient) -> Any:
    body: dict[str, Any] = {
        "source_text": args.text,
        "english_translation": args.english_translation,
        "token_persistence_mode": args.token_persistence_mode,
    }
    if args.target_json:
        body["target"] = parse_json_arg(args.target_json, "--target-json")
    return run_single(client, RequestSpec("POST", "/api/sentencebank/sentences", body=body))


def handle_verification_overview(args: argparse.Namespace, client: ApiClient) -> dict[str, Any]:
    details = get_lemma_details(client, args.lemma)
    return {"lemma": details.get("lemma"), "targets": collect_verification_targets(details)}


def handle_apply_action(args: argparse.Namespace, client: ApiClient) -> Any:
    details = get_lemma_details(client, args.lemma)
    target_spec = parse_target_spec(args.target)
    target = find_verification_target(details, target_spec)
    if target is None:
        raise DevAppError(f"Verification target not found: {args.target}")
    actions = (((target.get("verification") or {}).get("suggested_actions")) or [])
    if args.action_index < 0 or args.action_index >= len(actions):
        raise DevAppError(f"Action index {args.action_index} is out of range for target {args.target}.")
    body = {
        "stored_lemma": details.get("lemma") or args.lemma,
        "stored_surface_form": target["stored_surface_form"],
        "meaning_id": target["meaning_id"],
        "action": actions[args.action_index],
        "provider": (target.get("verification") or {}).get("provider"),
    }
    return run_single(client, RequestSpec("POST", "/api/wordbank/lexemes/apply-verification-changes", body=body))


def run_single(client: ApiClient, spec: RequestSpec) -> Any:
    return client.request(spec)


def get_lemma_details(client: ApiClient, lemma: str) -> dict[str, Any]:
    return client.request(RequestSpec("GET", f"/api/wordbank/lemmas/{quote_path(lemma)}"))


def scope_body(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "stored_lemma": args.lemma,
        "stored_surface_form": args.surface,
        "meaning_id": args.meaning_id,
    }


def cor_params(args: argparse.Namespace) -> dict[str, Any]:
    params = {
        "form": args.form,
        "limit": args.limit,
        "include_translations": args.include_translations,
    }
    if args.en_query:
        params["en_query"] = args.en_query
    if args.en_pos_ud:
        params["en_pos_ud"] = args.en_pos_ud
    return params


def collect_verification_targets(details: dict[str, Any]) -> list[dict[str, Any]]:
    targets: list[dict[str, Any]] = []
    lemma = str(details.get("lemma") or "")
    if details.get("verification"):
        targets.append(target_payload("lemma", lemma, "Lemma", None, None, details["verification"]))
    for section in details.get("meaning_sections") or []:
        meaning_id = section.get("id")
        label = section.get("english_translation") or section.get("gloss") or section.get("meaning_key") or lemma
        if section.get("verification"):
            targets.append(target_payload("meaning", str(label), f"Meaning #{meaning_id}", meaning_id, None, section["verification"]))
        for form in section.get("surface_forms") or []:
            if form.get("verification"):
                targets.append(target_payload("surface", form.get("form") or "", f"Variation in meaning #{meaning_id}", meaning_id, form.get("form"), form["verification"]))
    if not details.get("meaning_sections"):
        for form in details.get("surface_forms") or []:
            if form.get("verification"):
                targets.append(target_payload("surface", form.get("form") or "", "Variation", None, form.get("form"), form["verification"]))
    return targets


def target_payload(
    kind: str,
    label: str,
    scope_label: str,
    meaning_id: int | None,
    stored_surface_form: str | None,
    verification: dict[str, Any],
) -> dict[str, Any]:
    actions = verification.get("suggested_actions") or []
    return {
        "kind": kind,
        "label": label,
        "scope_label": scope_label,
        "meaning_id": meaning_id,
        "stored_surface_form": stored_surface_form,
        "status": verification.get("status"),
        "review_intent": verification.get("review_intent"),
        "message": verification.get("message"),
        "problem": verification.get("problem"),
        "change_to_implement": verification.get("change_to_implement"),
        "suggested_action_count": len(actions),
        "verification": verification,
    }


def find_verification_target(details: dict[str, Any], spec: TargetSpec) -> dict[str, Any] | None:
    for target in collect_verification_targets(details):
        if spec.kind != target["kind"]:
            continue
        if spec.meaning_id != target["meaning_id"]:
            continue
        if normalize(spec.surface_form) != normalize(target["stored_surface_form"]):
            continue
        return target
    return None


def parse_target_spec(raw: str) -> TargetSpec:
    if raw == "lemma":
        return TargetSpec("lemma")
    if raw.startswith("meaning:"):
        return TargetSpec("meaning", meaning_id=parse_target_meaning(raw.split(":", 1)[1]))
    if raw.startswith("surface:"):
        parts = raw.split(":", 2)
        if len(parts) != 3 or not parts[2]:
            raise DevAppError("Surface target must be surface:ID:FORM. Use root for no meaning id.")
        return TargetSpec("surface", meaning_id=parse_target_meaning(parts[1]), surface_form=parts[2])
    raise DevAppError("Target must be lemma, meaning:ID, or surface:ID:FORM.")


def parse_target_meaning(raw: str) -> int | None:
    if raw in {"root", "none", "null"}:
        return None
    try:
        return int(raw)
    except ValueError as exc:
        raise DevAppError(f"Invalid meaning id: {raw}") from exc


def translation_keys(groups: list[dict[str, Any]]) -> list[tuple[str, str, set[str]]]:
    labels: dict[str, str] = {}
    pos_by_key: dict[str, set[str]] = {}
    for group in groups:
        translation = str(group.get("danish_translation") or "").strip()
        if not translation:
            continue
        key = translation.lower()
        labels.setdefault(key, translation)
        pos = str(group.get("pos_ud") or "").strip().upper()
        if pos:
            pos_by_key.setdefault(key, set()).add(pos)
    return [(key, label, pos_by_key.get(key, set())) for key, label in labels.items()]


def flatten_cor_variants(payload: dict[str, Any]) -> list[dict[str, Any]]:
    flattened: list[dict[str, Any]] = []
    for group in payload.get("groups") or []:
        for variant in group.get("variants") or []:
            flattened.append(
                {
                    "cor_id": variant.get("cor_id"),
                    "lemma": variant.get("lemma"),
                    "form": variant.get("form"),
                    "pos_tag": variant.get("pos_tag"),
                    "gram_raw": variant.get("gram_raw"),
                    "gloss": group.get("gloss"),
                }
            )
    return flattened


def diff_cor_variants(unfiltered: dict[str, Any], filtered: dict[str, Any]) -> list[dict[str, Any]]:
    filtered_ids = {item.get("cor_id") for item in flatten_cor_variants(filtered)}
    return [{**item, "kept": item.get("cor_id") in filtered_ids} for item in flatten_cor_variants(unfiltered)]


def resolve_base_url(args: argparse.Namespace) -> str | None:
    if args.base_url:
        return probe(args.base_url.rstrip("/"), timeout=args.timeout)
    if args.host or args.port:
        host = args.host or "127.0.0.1"
        port = args.port or 8000
        return probe(f"http://{host}:{port}", timeout=args.timeout)
    detected = discover_uvicorn_port()
    candidates: list[tuple[str, int]] = []
    if detected:
        candidates.extend((host, detected) for host in DEFAULT_HOSTS)
    candidates.extend((host, port) for host in DEFAULT_HOSTS for port in DEFAULT_PORTS)
    seen: set[tuple[str, int]] = set()
    for host, port in candidates:
        if (host, port) in seen:
            continue
        seen.add((host, port))
        url = probe(f"http://{host}:{port}", timeout=min(args.timeout, 2.0))
        if url:
            return url
    return None


def discover_uvicorn_port() -> int | None:
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


def probe(base: str, *, timeout: float) -> str | None:
    try:
        with urllib.request.urlopen(f"{base}/api/health", timeout=timeout) as response:
            if response.status == 200:
                return base
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    return None


def success_envelope(command: str, client: ApiClient, response: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "command": command,
        "base_url": client.base_url,
        "request": client.timings[-1]["request"] if client.timings else None,
        "response": response,
        "timings_ms": client.timings,
    }


def error_envelope(command: str, args: argparse.Namespace, exc: DevAppError) -> dict[str, Any]:
    return {
        "ok": False,
        "command": command,
        "base_url": args.base_url,
        "request": exc.request,
        "status": exc.status,
        "error": str(exc),
        "body": exc.body,
    }


def request_payload(spec: RequestSpec) -> dict[str, Any]:
    payload: dict[str, Any] = {"method": spec.method, "path": spec.path}
    if spec.params:
        payload["params"] = spec.params
    if spec.body is not None:
        payload["body"] = spec.body
    return payload


def _timing(spec: RequestSpec, elapsed_ms: float, *, status: int | None) -> dict[str, Any]:
    return {
        "request": request_payload(spec),
        "status": status,
        "elapsed_ms": round(elapsed_ms, 3),
    }


def _query_string(params: dict[str, Any]) -> str:
    clean = {key: json_bool(value) for key, value in params.items() if value is not None}
    return urllib.parse.urlencode(clean)


def _decode_json(raw: bytes) -> Any:
    if not raw:
        return None
    text = raw.decode("utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def parse_json_arg(value: str, label: str) -> Any:
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise DevAppError(f"{label} must be valid JSON: {exc.msg}") from exc


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"invalid boolean value: {value}")


def json_bool(value: Any) -> Any:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def quote_path(value: str) -> str:
    return urllib.parse.quote(value, safe="")


def normalize(value: str | None) -> str | None:
    normalized = (value or "").strip().lower()
    return normalized or None


def print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    sys.exit(main())

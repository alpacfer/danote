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


def _add_wordbank_parser(subparsers: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = subparsers.add_parser("wordbank", help="Wordbank commands.")
    child = parser.add_subparsers(dest="wordbank_command", required=True)

    _set_handler(child.add_parser("list", help="List saved lemmas."), ["wordbank", "list"], lambda _args, client: run_single(client, RequestSpec("GET", "/api/wordbank/lemmas")))

    details = child.add_parser("details", help="Read lemma details.")
    details.add_argument("lemma")
    _set_handler(details, ["wordbank", "details"], lambda args, client: get_lemma_details(client, args.lemma))

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

"""Unified DerekOS operator CLI."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Callable

from .candidate_intake import CandidateIntake
from .config import RuntimeConfig
from .diagnostics import run_diagnostics
from .ingest import run_ingest
from .publisher import ManagedProjectionPublisher
from .repository import ReadOnlyCanonicalRepository
from .review_workflow import ReviewWorkflow
from .storage import BulkResult

LOGGER = logging.getLogger(__name__)


def _json_default(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _emit(value: Any, *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(value, default=_json_default, ensure_ascii=False, sort_keys=True))
        return
    data = value.to_dict() if hasattr(value, "to_dict") else value
    if isinstance(data, dict) and {"status", "success_count", "failure_count"} <= set(data):
        print(f"{data['operation']}: {data['status']} ({data['success_count']} succeeded, {data['failure_count']} failed)")
        for failure in data.get("failures", []):
            print(f"  FAIL {failure['identifier']}: {failure['message']}")
    elif isinstance(data, dict) and "checks" in data:
        print(f"doctor: {data['status']}")
        for check in data["checks"]:
            print(f"  {check['status'].upper():5} {check['name']}: {check['message']}")
    elif isinstance(data, list):
        for item in data:
            print(json.dumps(item, ensure_ascii=False, sort_keys=True))
    else:
        print(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2))


def _repository() -> ReadOnlyCanonicalRepository:
    return ReadOnlyCanonicalRepository.from_environment()


def _publisher() -> ManagedProjectionPublisher:
    return ManagedProjectionPublisher.from_environment(_repository())


def _intake() -> CandidateIntake:
    return CandidateIntake.from_environment(repository=_repository())


def _review() -> ReviewWorkflow:
    return ReviewWorkflow.from_environment(_repository())


def _bulk_exit(result: BulkResult) -> int:
    return 0 if result.ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="derekos", description="DerekOS Master Brain operator CLI")
    parser.add_argument("--json", action="store_true", dest="json_output", help="emit stable JSON")
    parser.add_argument("--log-level", default="WARNING", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("doctor", help="read-only readiness diagnostics")

    ingest = sub.add_parser("ingest", help="run deterministic Phase 1 ingest")
    ingest.add_argument("--source-dir", type=Path)
    ingest.add_argument("--output-dir", type=Path)
    ingest.add_argument("--index-dir", type=Path)

    get = sub.add_parser("get", help="get canonical knowledge by ID")
    get.add_argument("knowledge_id")
    get.add_argument("--revision", type=int)

    search = sub.add_parser("search", help="search canonical knowledge")
    search.add_argument("query")
    search.add_argument("--include-history", action="store_true")
    search.add_argument("--limit", type=int, default=10)

    publish = sub.add_parser("publish", help="publish one managed projection")
    publish.add_argument("knowledge_id")
    publish.add_argument("--revision", type=int)
    sub.add_parser("publish-all", help="publish all publishable CURRENT projections")

    intake = sub.add_parser("intake", help="intake one candidate note")
    intake.add_argument("source_path", type=Path)
    sub.add_parser("intake-all", help="intake every candidate note")

    review = sub.add_parser("review", help="review one candidate")
    review.add_argument("candidate_id")
    sub.add_parser("review-all", help="review every pending candidate")
    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "doctor":
        report = run_diagnostics(RuntimeConfig.load())
        _emit(report, json_output=args.json_output)
        return 0 if report.ok else 1
    if args.command == "ingest":
        report = run_ingest(args.source_dir, args.output_dir, args.index_dir)
        _emit(report, json_output=args.json_output)
        return 0 if report.ok else 1
    if args.command == "get":
        _emit(_repository().get(args.knowledge_id, revision=args.revision), json_output=args.json_output)
        return 0
    if args.command == "search":
        _emit(_repository().search(args.query, include_history=args.include_history, limit=args.limit), json_output=args.json_output)
        return 0
    if args.command == "publish":
        _emit(_publisher().publish(args.knowledge_id, revision=args.revision), json_output=args.json_output)
        return 0
    if args.command == "publish-all":
        result = _publisher().publish_all_current()
        _emit(result, json_output=args.json_output)
        return _bulk_exit(result)
    if args.command == "intake":
        _emit(_intake().ingest(args.source_path), json_output=args.json_output)
        return 0
    if args.command == "intake-all":
        result = _intake().ingest_all()
        _emit(result, json_output=args.json_output)
        return _bulk_exit(result)
    if args.command == "review":
        _emit(_review().review_candidate(args.candidate_id), json_output=args.json_output)
        return 0
    if args.command == "review-all":
        result = _review().review_all_pending()
        _emit(result, json_output=args.json_output)
        return _bulk_exit(result)
    raise AssertionError(args.command)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    normalized_argv = list(sys.argv[1:] if argv is None else argv)
    if "--json" in normalized_argv:
        normalized_argv = [item for item in normalized_argv if item != "--json"]
        normalized_argv.insert(0, "--json")
    args = parser.parse_args(normalized_argv)
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(levelname)s:%(name)s:%(message)s")
    try:
        return run(args)
    except Exception as exc:  # noqa: BLE001 - CLI translates all failures to operator errors.
        if args.log_level == "DEBUG":
            LOGGER.exception("command failed")
        if args.json_output:
            print(json.dumps({"status": "error", "error_type": type(exc).__name__, "message": str(exc)}, sort_keys=True))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

"""Read-only readiness diagnostics for the Master Brain operator surface."""

from __future__ import annotations

import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .extraction import ExtractionPipeline
from .repository import CanonicalStoreInvalid, CanonicalStoreUnavailable, ReadOnlyCanonicalRepository


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass(frozen=True)
class DiagnosticReport:
    status: str
    checks: list[DiagnosticCheck] = field(default_factory=list)
    config: dict[str, str | None] = field(default_factory=dict)
    runtime: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status == "ready"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "checks": [check.to_dict() for check in self.checks],
            "config": self.config,
            "runtime": self.runtime,
        }


def _check_file(name: str, path: Path, message: str) -> DiagnosticCheck:
    if path.is_file():
        return DiagnosticCheck(name, "ok", message, str(path))
    return DiagnosticCheck(name, "fail", f"missing required file: {path}", str(path))


def _check_dir(name: str, path: Path, message: str) -> DiagnosticCheck:
    if path.is_dir():
        return DiagnosticCheck(name, "ok", message, str(path))
    return DiagnosticCheck(name, "fail", f"missing required directory: {path}", str(path))


def run_diagnostics(config: RuntimeConfig | None = None) -> DiagnosticReport:
    """Inspect prerequisites without creating, repairing, or mutating files."""

    cfg = config or RuntimeConfig.load()
    checks: list[DiagnosticCheck] = []
    checks.append(DiagnosticCheck(
        "python_version",
        "ok" if sys.version_info >= (3, 11) else "fail",
        f"Python {platform.python_version()} (requires >=3.11)",
    ))
    checks.append(_check_dir("raw_chatgpt_dir", cfg.raw_chatgpt_dir, "raw ChatGPT source directory exists"))
    if cfg.raw_chatgpt_dir.is_dir():
        has_sources = any(cfg.raw_chatgpt_dir.glob("conversations-*.json"))
        checks.append(DiagnosticCheck(
            "raw_chatgpt_sources",
            "ok" if has_sources else "fail",
            "found conversations-*.json" if has_sources else "no conversations-*.json files found",
            str(cfg.raw_chatgpt_dir),
        ))
    checks.append(_check_file("ingest_schema", cfg.repo_root / "01_INGEST" / "schemas" / "message-1.1.0.schema.json", "ingest schema is present"))
    checks.append(DiagnosticCheck("extraction_implementation", "ok", "extraction pipeline is importable"))
    for schema_name in ("thought.schema.json", "entity.schema.json", "relationship.schema.json", "timeline.schema.json", "canonical-candidate.schema.json"):
        schema_path = cfg.repo_root / "schemas" / schema_name
        if not schema_path.is_file():
            checks.append(DiagnosticCheck(f"extraction_schema_{schema_name}", "fail", f"missing required extraction schema: {schema_name}", str(schema_path)))
            continue
        try:
            parsed = json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            checks.append(DiagnosticCheck(f"extraction_schema_{schema_name}", "fail", f"invalid schema JSON: {exc}", str(schema_path)))
        else:
            checks.append(DiagnosticCheck(
                f"extraction_schema_{schema_name}",
                "ok" if isinstance(parsed, dict) and parsed.get("type") == "object" else "fail",
                "extraction schema is installed" if isinstance(parsed, dict) and parsed.get("type") == "object" else "extraction schema must be a JSON object schema",
                str(schema_path),
            ))
    try:
        repo = ReadOnlyCanonicalRepository(cfg.canonical_store_path)
    except (CanonicalStoreUnavailable, CanonicalStoreInvalid) as exc:
        checks.append(DiagnosticCheck("canonical_store", "fail", str(exc), str(cfg.canonical_store_path)))
    else:
        checks.append(DiagnosticCheck("canonical_store", "ok", f"canonical store valid ({len(repo.knowledge_ids)} knowledge IDs)", str(cfg.canonical_store_path)))
    if cfg.obsidian_vault_path is None:
        checks.append(DiagnosticCheck("obsidian_vault", "fail", "OBSIDIAN_VAULT_PATH not configured"))
    else:
        checks.append(_check_dir("obsidian_vault", cfg.obsidian_vault_path, "Obsidian vault exists"))
        managed = cfg.obsidian_vault_path / "MasterBrain"
        checks.append(DiagnosticCheck(
            "managed_vault_parent",
            "ok" if managed.exists() or cfg.obsidian_vault_path.is_dir() else "fail",
            "managed subtree parent can be addressed" if cfg.obsidian_vault_path.is_dir() else "vault unavailable",
            str(managed),
        ))
    checks.append(DiagnosticCheck(
        "candidate_queue_parent",
        "ok" if cfg.candidate_queue_path.parent.exists() else "warn",
        "candidate queue parent exists" if cfg.candidate_queue_path.parent.exists() else "candidate queue parent will be needed before intake",
        str(cfg.candidate_queue_path.parent),
    ))
    checks.append(DiagnosticCheck(
        "review_log_parent",
        "ok" if cfg.review_log_path.parent.exists() else "warn",
        "review log parent exists" if cfg.review_log_path.parent.exists() else "review log parent will be needed before review",
        str(cfg.review_log_path.parent),
    ))
    for artifact in ("messages.jsonl", "conversations_index.json", "ingest_report.json"):
        path = cfg.ingest_output_dir / artifact
        checks.append(DiagnosticCheck(
            f"ingest_artifact_{artifact}",
            "ok" if path.is_file() else "warn",
            f"generated artifact present: {artifact}" if path.is_file() else f"generated artifact absent: {artifact}",
            str(path),
        ))
    pipeline = ExtractionPipeline(cfg)
    stage_artifacts = (
        ("thoughts", cfg.thoughts_path, pipeline._validate_thought),
        ("entities", cfg.entities_path, pipeline._validate_entity),
        ("relationships", cfg.relationships_path, pipeline._validate_relationship),
        ("timelines", cfg.timelines_path, pipeline._validate_timeline),
        ("canonical_candidates", cfg.canonical_candidates_path, pipeline._validate_canonical),
    )
    for name, path, validator in stage_artifacts:
        if not path.is_file():
            checks.append(DiagnosticCheck(f"extraction_artifact_{name}", "warn", f"optional generated extraction artifact absent: {path.name}", str(path)))
            continue
        try:
            count = 0
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if not line.strip():
                    continue
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError(f"line {line_number} must be an object")
                validator(record, f"{path.name} line {line_number}")
                count += 1
        except Exception as exc:  # noqa: BLE001 - diagnostics reports invalid optional artifacts.
            checks.append(DiagnosticCheck(f"extraction_artifact_{name}", "fail", f"generated extraction artifact invalid: {exc}", str(path)))
        else:
            checks.append(DiagnosticCheck(f"extraction_artifact_{name}", "ok", f"generated extraction artifact valid ({count} records)", str(path)))
    status = "ready" if all(check.status != "fail" for check in checks) else "not_ready"
    return DiagnosticReport(
        status=status,
        checks=checks,
        config=cfg.redacted(),
        runtime={"python": platform.python_version(), "platform": platform.platform()},
    )


def dumps(report: DiagnosticReport) -> str:
    return json.dumps(report.to_dict(), sort_keys=True)

"""One-way candidate intake from Obsidian MasterBrain/Candidates/ to Master Brain Candidate Queue.

This module reads candidate notes from the Obsidian vault's candidate subtree and
creates candidate records in a local queue. It never modifies the Evidence Store,
Canonical Store, Published projections, or VOX operational state. Even ACCEPTED
status does not mutate canonical knowledge — that belongs to a later review/commit workflow.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RuntimeConfig
from .repository import CanonicalKnowledgeNotFound, ReadOnlyCanonicalRepository
from .storage import BulkResult, StorageError, append_jsonl, read_jsonl

LOGGER = logging.getLogger(__name__)

CANDIDATE_SUBTREE = "MasterBrain/Candidates"
PUBLISHED_SUBTREE = "MasterBrain/Published"
MANAGED_FRONTMATTER_KEY = "master_brain_managed"

ALLOWED_OPERATIONS = {"CREATE", "UPDATE", "SUPERSEDE", "RETIRE", "UNKNOWN"}

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


class CandidateIntakeError(RuntimeError):
    """Base exception for candidate intake failures."""


class CandidateSourceInvalid(CandidateIntakeError):
    """The candidate source violates the intake contract."""


class CandidatePathError(CandidateIntakeError):
    """The candidate source path is outside the allowed subtree."""


class CandidateQueueError(CandidateIntakeError):
    """The candidate queue is invalid or unavailable."""


class CandidateIntake:
    """Reads candidate notes from Obsidian and creates candidate records.

    This intake is one-way: Obsidian MasterBrain/Candidates/ → Master Brain Candidate Queue.
    It never modifies the Evidence Store, Canonical Store, Published projections, or VOX state.
    Intake is idempotent: re-reading an unchanged candidate does not create duplicates.
    """

    def __init__(
        self,
        vault_root: str | os.PathLike[str],
        queue_path: str | os.PathLike[str],
        *,
        repository: ReadOnlyCanonicalRepository | None = None,
        candidate_subtree: str = CANDIDATE_SUBTREE,
        submitter_identity: str = "human",
        vault_id: str = "vox-primary-curated-vault",
    ) -> None:
        self._vault_root = Path(vault_root).expanduser().resolve(strict=False)
        if not self._vault_root.is_dir():
            raise CandidateIntakeError("vault root must be an existing directory")
        if Path(candidate_subtree).as_posix() != CANDIDATE_SUBTREE:
            raise CandidatePathError("candidate subtree must be exactly MasterBrain/Candidates")
        if not isinstance(submitter_identity, str) or not submitter_identity.strip():
            raise CandidateIntakeError("submitter_identity must be explicit")
        self._queue_path = Path(queue_path).expanduser().resolve(strict=False)
        self._repository = repository
        self._candidate_subtree = candidate_subtree
        self._submitter_identity = submitter_identity.strip()
        self._vault_id = vault_id
        self._candidates_root = self._vault_root / candidate_subtree
        self._published_root = self._vault_root / PUBLISHED_SUBTREE

    @classmethod
    def from_environment(
        cls,
        *,
        repository: ReadOnlyCanonicalRepository | None = None,
        queue_path: str | os.PathLike[str] | None = None,
    ) -> "CandidateIntake":
        """Create the intake from environment variables."""

        config = RuntimeConfig.load()
        vault_path = config.obsidian_vault_path
        if vault_path is None:
            raise CandidateIntakeError("OBSIDIAN_VAULT_PATH not configured")
        if queue_path is None:
            queue_path = config.candidate_queue_path
        return cls(vault_path, queue_path, repository=repository)

    @property
    def candidates_root(self) -> Path:
        return self._candidates_root

    @property
    def queue_path(self) -> Path:
        return self._queue_path

    def ingest(self, source_path: str | Path) -> dict[str, Any]:
        """Ingest one candidate note and return the candidate record.

        If the source has not changed (by hash), returns the existing candidate record
        without creating a duplicate. Raises CandidatePathError if the source is outside
        the candidate subtree or inside the published subtree.
        """

        resolved = self._resolve_and_validate_path(source_path)
        self._assert_not_published(resolved)

        content = resolved.read_text(encoding="utf-8")
        source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        relative_path = resolved.relative_to(self._vault_root).as_posix()
        existing = self._find_existing(relative_path, source_hash)
        if existing is not None:
            self._log_intake("ingest_no_op", existing)
            return existing

        frontmatter = self._parse_frontmatter(content)
        body = self._extract_body(content)
        record = self._build_candidate_record(resolved, source_hash, frontmatter, body)
        self._append_to_queue(record)
        self._log_intake("ingest", record)
        return record

    def ingest_all(self) -> BulkResult:
        """Ingest all candidate notes and return structured per-item outcomes."""

        result = BulkResult("candidate_intake_all")
        if not self._candidates_root.is_dir():
            return result
        for md_file in sorted(self._candidates_root.rglob("*.md")):
            if not md_file.is_file() or md_file.is_symlink():
                continue
            try:
                record = self.ingest(md_file)
                result.add_success(record)
            except CandidateIntakeError as exc:
                result.add_failure(md_file.relative_to(self._vault_root).as_posix(), exc)
                LOGGER.warning("ingest_all failed source=%s error=%s", md_file.relative_to(self._vault_root).as_posix(), exc)
        return result

    def _resolve_and_validate_path(self, source_path: str | Path) -> Path:
        requested = Path(source_path).expanduser()
        if not requested.is_absolute():
            requested = self._vault_root / requested
        resolved = requested.resolve(strict=False)
        candidates_resolved = self._candidates_root.resolve()
        vault_resolved = self._vault_root.resolve()
        try:
            candidates_resolved.relative_to(vault_resolved)
        except ValueError as exc:
            raise CandidatePathError(f"candidate subtree escapes vault root: {self._candidates_root}") from exc
        try:
            resolved.relative_to(candidates_resolved)
        except ValueError as exc:
            raise CandidatePathError(f"candidate source outside candidate subtree: {resolved}") from exc
        if not resolved.is_file():
            raise CandidateSourceInvalid(f"candidate source is not a regular file: {resolved}")
        if resolved.is_symlink():
            raise CandidateSourceInvalid(f"candidate source is a symlink: {resolved}")
        return resolved

    def _assert_not_published(self, resolved: Path) -> None:
        published_resolved = self._published_root.resolve()
        try:
            resolved.relative_to(published_resolved)
            raise CandidatePathError(f"candidate source is inside published subtree: {resolved}")
        except ValueError:
            pass

    @staticmethod
    def _parse_frontmatter(content: str) -> dict[str, Any]:
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            return {}
        frontmatter_text = match.group(1)
        result: dict[str, Any] = {}
        for line in frontmatter_text.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
                value = value[1:-1]
            elif len(value) >= 2 and value[0] == "'" and value[-1] == "'":
                value = value[1:-1]
            if value.lower() == "true":
                result[key] = True
            elif value.lower() == "false":
                result[key] = False
            elif value.lstrip("-").isdigit():
                result[key] = int(value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _extract_body(content: str) -> str:
        match = FRONTMATTER_PATTERN.match(content)
        if match:
            return content[match.end():].strip()
        return content.strip()

    def _build_candidate_record(
        self,
        source_path: Path,
        source_hash: str,
        frontmatter: dict[str, Any],
        body: str,
    ) -> dict[str, Any]:
        relative_path = source_path.relative_to(self._vault_root).as_posix()
        prior_revisions = [
            record for record in self._read_queue()
            if record.get("source_path") == relative_path
        ]
        candidate_id = self._generate_candidate_id(relative_path)
        candidate_revision = 1 + max((int(item.get("candidate_revision", 0)) for item in prior_revisions), default=0)

        proposed_operation = self._normalize_operation(frontmatter.get("proposed_operation"))
        proposed_knowledge_id = self._normalize_knowledge_id(frontmatter.get("proposed_knowledge_id"))
        base_revision = self._normalize_base_revision(frontmatter.get("base_canonical_revision"))

        if proposed_knowledge_id and self._repository is not None:
            self._validate_against_canonical(proposed_knowledge_id, base_revision)

        status = self._determine_initial_status(frontmatter, proposed_knowledge_id, base_revision)
        provenance_refs = self._normalize_provenance_refs(frontmatter.get("provenance_refs", frontmatter.get("evidence_refs")))

        record = {
            "candidate_id": candidate_id,
            "candidate_revision": candidate_revision,
            "source_system": "obsidian",
            "source_path": relative_path,
            "source_hash": source_hash,
            "source_identity": {
                "vault_id": self._vault_id,
                "relative_path": relative_path,
                "source_sha256": source_hash,
            },
            "submitted_at": datetime.now(timezone.utc).isoformat(),
            "candidate_type": self._normalize_candidate_type(frontmatter.get("candidate_type")),
            "proposed_knowledge_id": proposed_knowledge_id,
            "proposed_operation": proposed_operation,
            "base_canonical_revision": base_revision,
            "submitter": self._submitter_identity,
            "claimed_submitter": frontmatter.get("submitter"),
            "provenance_refs": provenance_refs,
            "evidence_ids": provenance_refs,
            "status": status,
            "content_summary": body[:500] if body else "",
            "content": body,
            "content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "submitted_content_hash": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            "intake_schema": 1,
        }
        return record

    @staticmethod
    def _generate_candidate_id(relative_path: str) -> str:
        return f"MBC-{hashlib.sha256(relative_path.encode('utf-8')).hexdigest()[:16].upper()}"

    @staticmethod
    def _normalize_operation(value: Any) -> str:
        if isinstance(value, str) and value.strip().upper() in ALLOWED_OPERATIONS:
            return value.strip().upper()
        return "UNKNOWN"

    @staticmethod
    def _normalize_knowledge_id(value: Any) -> str | None:
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    @staticmethod
    def _normalize_base_revision(value: Any) -> int | None:
        if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
            return value
        if isinstance(value, str) and value.strip().isdigit():
            parsed = int(value.strip())
            return parsed if parsed >= 1 else None
        return None

    @staticmethod
    def _normalize_candidate_type(value: Any) -> str:
        if isinstance(value, str) and value.strip().upper() in {"NEW", "UPDATE", "SUPERSEDE", "RETIRE", "ANNOTATION"}:
            return value.strip().upper()
        return "UNKNOWN"

    @staticmethod
    def _normalize_provenance_refs(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if isinstance(item, str) and str(item).strip()]
        if isinstance(value, str) and value.strip():
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _validate_against_canonical(self, knowledge_id: str, base_revision: int | None) -> None:
        if self._repository is None:
            return
        try:
            current = self._repository.get(knowledge_id)
            if base_revision is not None and base_revision < current["revision"]:
                LOGGER.info(
                    "candidate references stale revision %s (base=%d, current=%d)",
                    knowledge_id, base_revision, current["revision"],
                )
        except CanonicalKnowledgeNotFound:
            LOGGER.info("candidate references unknown knowledge_id: %s", knowledge_id)

    def _determine_initial_status(
        self,
        frontmatter: dict[str, Any],
        proposed_knowledge_id: str | None,
        base_revision: int | None,
    ) -> str:
        if not proposed_knowledge_id:
            return "SUBMITTED"

        if self._repository is None:
            return "SUBMITTED"

        try:
            current = self._repository.get(proposed_knowledge_id)
        except CanonicalKnowledgeNotFound:
            return "SUBMITTED"

        if base_revision is not None and base_revision < current["revision"]:
            return "CONFLICT_OPEN"
        return "REVIEW_READY"

    def _find_existing(self, source_path: str, source_hash: str) -> dict[str, Any] | None:
        if not self._queue_path.is_file():
            return None
        for record in self._read_queue():
            if record.get("source_path") == source_path and record.get("source_hash") == source_hash:
                return record
        return None

    def _read_queue(self) -> list[dict[str, Any]]:
        try:
            return read_jsonl(self._queue_path)
        except StorageError as exc:
            raise CandidateQueueError(str(exc)) from exc

    def _append_to_queue(self, record: dict[str, Any]) -> None:
        try:
            append_jsonl(self._queue_path, record)
        except StorageError as exc:
            raise CandidateQueueError(str(exc)) from exc

    @staticmethod
    def _log_intake(operation: str, record: dict[str, Any]) -> None:
        LOGGER.info(
            "master_brain_candidate_intake operation=%s candidate_id=%s source=%s status=%s operation_type=%s",
            operation,
            record["candidate_id"],
            record["source_path"],
            record["status"],
            record["proposed_operation"],
        )

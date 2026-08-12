"""One-way managed projection from Master Brain canonical store to Obsidian.

This module publishes accepted canonical knowledge records as human-readable
Obsidian notes in a managed projection subtree. It never overwrites human-authored
notes and never writes outside the managed region.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .repository import ReadOnlyCanonicalRepository

LOGGER = logging.getLogger(__name__)

PROJECTION_SCHEMA_VERSION = 1
MANAGED_FRONTMATTER_KEY = "master_brain_managed"
MANAGED_SUBTREE = "MasterBrain/Published"

FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
SAFE_KNOWLEDGE_ID = re.compile(r"^MBK-[A-Z0-9-]+$")


class ProjectionError(RuntimeError):
    """Base exception for projection failures."""


class PathCollisionError(ProjectionError):
    """A human-authored note exists at the target projection path."""


class UnauthorizedWriteError(ProjectionError):
    """Attempted write outside the managed projection subtree."""


class CanonicalRecordInvalid(ProjectionError):
    """The canonical record violates the projection contract."""


class ManagedProjectionPublisher:
    """Publishes canonical records as managed Obsidian projections.

    This publisher is one-way: Master Brain Canonical Store → Obsidian managed subtree.
    It never overwrites human-authored notes and never writes outside the managed region.
    Publishing is idempotent: if the canonical revision has not changed, the note is not rewritten.
    """

    def __init__(
        self,
        repository: ReadOnlyCanonicalRepository,
        vault_root: str | os.PathLike[str],
        *,
        projection_subtree: str = MANAGED_SUBTREE,
    ) -> None:
        self._repository = repository
        self._vault_root = Path(vault_root).expanduser().resolve(strict=False)
        if not self._vault_root.is_dir():
            raise ProjectionError("vault root must be an existing directory")
        if Path(projection_subtree).as_posix() != MANAGED_SUBTREE:
            raise UnauthorizedWriteError("projection subtree must be exactly MasterBrain/Published")
        self._projection_subtree = projection_subtree
        self._managed_root = self._vault_root / projection_subtree

    @classmethod
    def from_environment(cls, repository: ReadOnlyCanonicalRepository) -> "ManagedProjectionPublisher":
        """Create the publisher from the canonical Obsidian vault path."""

        vault_path = os.getenv("OBSIDIAN_VAULT_PATH")
        if not vault_path:
            raise ProjectionError("OBSIDIAN_VAULT_PATH not configured")
        return cls(repository, vault_path)

    @property
    def managed_root(self) -> Path:
        return self._managed_root

    def publish(self, knowledge_id: str, *, revision: int | None = None) -> dict[str, Any]:
        """Publish one canonical record as a managed Obsidian note.

        If revision is None, publishes the CURRENT revision. If the canonical
        revision has not changed (by hash), the note is not rewritten. Returns
        a projection receipt with the outcome.
        """

        record = self._repository.get(knowledge_id, revision=revision)
        self._validate_record_for_projection(record)

        note_path = self._resolve_note_path(record)
        self._ensure_managed_subtree(note_path)
        canonical_hash = self._hash_canonical_record(record)
        note_content = self._render_note(record, canonical_hash)
        existing = self._read_existing(note_path, record)

        if existing == note_content:
            receipt = self._receipt(record, note_path, action="no_op", canonical_hash=canonical_hash)
            self._log_projection("publish_no_op", receipt)
            return receipt
        if existing is not None:
            self._assert_safe_upgrade(existing, record)
        self._write_note_atomic(note_path, note_content)

        receipt = self._receipt(record, note_path, action="published", canonical_hash=canonical_hash)
        self._log_projection("publish", receipt)
        return receipt

    def publish_all_current(self) -> list[dict[str, Any]]:
        """Publish all CURRENT canonical records. Returns receipts."""

        receipts: list[dict[str, Any]] = []
        for knowledge_id in self._all_knowledge_ids():
            try:
                record = self._repository.get(knowledge_id)
                if not self._is_publishable(record):
                    continue
                receipt = self.publish(knowledge_id)
                receipts.append(receipt)
            except ProjectionError as exc:
                LOGGER.warning("publish_all_current skipped %s: %s", knowledge_id, exc)
        return receipts

    def _validate_record_for_projection(self, record: dict[str, Any]) -> None:
        required = {"knowledge_id", "revision", "canonical_status", "title", "content", "evidence_ids"}
        missing = required - set(record.keys())
        if missing:
            raise CanonicalRecordInvalid(f"canonical record missing fields: {missing}")
        if not record["knowledge_id"].strip():
            raise CanonicalRecordInvalid("canonical record has empty knowledge_id")
        if not record["title"].strip():
            raise CanonicalRecordInvalid("canonical record has empty title")
        if not SAFE_KNOWLEDGE_ID.fullmatch(record["knowledge_id"]):
            raise CanonicalRecordInvalid("knowledge_id is unsafe for projection")
        if not self._is_publishable(record):
            raise CanonicalRecordInvalid(
                "projection requires CURRENT canonical_status, ACCEPTED approval_status, and PUBLISH projection_policy"
            )
        if record.get("source_authority") != "MASTER_BRAIN_CANONICAL_STORE":
            raise CanonicalRecordInvalid("record was not resolved from canonical authority")

    @staticmethod
    def _is_publishable(record: dict[str, Any]) -> bool:
        return (
            record.get("canonical_status") == "CURRENT"
            and record.get("approval_status") == "ACCEPTED"
            and record.get("projection_policy") == "PUBLISH"
        )

    def _resolve_note_path(self, record: dict[str, Any]) -> Path:
        filename = f"{record['knowledge_id']}.md"
        return self._managed_root / filename

    @staticmethod
    def _slugify(text: str) -> str:
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_]+", "-", slug)
        slug = re.sub(r"-+", "-", slug)
        return slug[:80].strip("-") or "untitled"

    def _ensure_managed_subtree(self, note_path: Path) -> None:
        resolved = note_path.resolve()
        managed_resolved = self._managed_root.resolve()
        vault_resolved = self._vault_root.resolve()
        try:
            managed_resolved.relative_to(vault_resolved)
        except ValueError as exc:
            raise UnauthorizedWriteError(
                f"managed subtree escapes vault root: {self._managed_root}"
            ) from exc
        try:
            resolved.relative_to(managed_resolved)
        except ValueError as exc:
            raise UnauthorizedWriteError(
                f"projection path escapes managed subtree: {note_path}"
            ) from exc
        self._managed_root.mkdir(parents=True, exist_ok=True)

    def _read_existing(self, note_path: Path, record: dict[str, Any]) -> str | None:
        if not note_path.exists():
            return None
        if note_path.is_symlink() or not note_path.is_file():
            raise PathCollisionError(f"projection target is not a regular file: {note_path}")
        content = note_path.read_text(encoding="utf-8")
        frontmatter = self._parse_frontmatter(content)
        if frontmatter.get(MANAGED_FRONTMATTER_KEY) is not True:
            raise PathCollisionError(f"human-authored note exists at projection path: {note_path}")
        if frontmatter.get("knowledge_id") != record["knowledge_id"]:
            raise PathCollisionError(f"managed note for different knowledge_id exists at path: {note_path}")
        return content

    def _assert_safe_upgrade(self, existing: str, incoming: dict[str, Any]) -> None:
        frontmatter = self._parse_frontmatter(existing)
        existing_revision = frontmatter.get("canonical_revision")
        if not isinstance(existing_revision, int):
            raise PathCollisionError("managed projection has no valid canonical_revision")
        match = FRONTMATTER_PATTERN.match(existing)
        body = existing[match.end():] if match else ""
        projected_body_hash = frontmatter.get("projected_body_sha256")
        if not isinstance(projected_body_hash, str) or hashlib.sha256(body.encode("utf-8")).hexdigest() != projected_body_hash:
            raise PathCollisionError("managed projection contains human or out-of-band changes")
        if incoming["revision"] <= existing_revision:
            raise PathCollisionError("projection revision is not a monotonic upgrade")

    @staticmethod
    def _hash_canonical_record(record: dict[str, Any]) -> str:
        canonical_form = {
            "knowledge_id": record["knowledge_id"],
            "revision": record["revision"],
            "canonical_status": record["canonical_status"],
            "title": record["title"],
            "summary": record.get("summary", ""),
            "content": record["content"],
            "evidence_ids": sorted(record.get("evidence_ids", [])),
        }
        serialized = json.dumps(canonical_form, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

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
            elif value.isdigit():
                result[key] = int(value)
            else:
                result[key] = value
        return result

    def _render_note(self, record: dict[str, Any], canonical_hash: str) -> str:
        body_lines = [
            f"# {record['title']}",
            "",
        ]
        if record.get("summary"):
            body_lines.extend([
                f"*{record['summary']}*",
                "",
            ])
        body_lines.extend([
            "## Content",
            "",
            record["content"],
            "",
            "## Provenance",
            "",
            f"- **Knowledge ID:** {record['knowledge_id']}",
            f"- **Revision:** {record['revision']}",
            f"- **Status:** {record['canonical_status']}",
            f"- **Evidence IDs:** {', '.join(record.get('evidence_ids', [])) or 'none'}",
            "",
            "---",
            "*This note is a managed projection of canonical Master Brain knowledge.*",
            "*It is not the authoritative source. Edits require candidate review.*",
        ])
        body = "\n".join(body_lines) + "\n"
        frontmatter = {
            MANAGED_FRONTMATTER_KEY: True,
            "knowledge_id": record["knowledge_id"],
            "canonical_revision": record["revision"],
            "canonical_status": record["canonical_status"].lower(),
            "approval_status": record["approval_status"].lower(),
            "projection_policy": record["projection_policy"].lower(),
            "projection_schema": PROJECTION_SCHEMA_VERSION,
            "source_authority": "MASTER_BRAIN_CANONICAL_STORE",
            "canonical_hash": canonical_hash,
            "projected_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
        frontmatter_lines = [f"{key}: {self._yaml_value(value)}" for key, value in frontmatter.items()]
        frontmatter_block = "---\n" + "\n".join(frontmatter_lines) + "\n---\n\n"

        return frontmatter_block + body

    @staticmethod
    def _yaml_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if any(char in value for char in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", ">", "<", "!", "%", "@", "`", '"', "'")):
                return f'"{value}"'
            if value and value[0] in (" ", "-"):
                return f'"{value}"'
            return value
        return str(value)

    def _write_note_atomic(self, note_path: Path, content: str) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=note_path.parent,
                prefix=f".{note_path.stem}.",
                suffix=".tmp",
                delete=False,
            ) as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
                temp_path = Path(output.name)
            temp_path.replace(note_path)
        except OSError as exc:
            raise ProjectionError(f"failed to write projection: {note_path}") from exc
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    def _receipt(
        self,
        record: dict[str, Any],
        note_path: Path,
        *,
        action: str,
        canonical_hash: str,
    ) -> dict[str, Any]:
        return {
            "knowledge_id": record["knowledge_id"],
            "revision": record["revision"],
            "canonical_status": record["canonical_status"],
            "projection_path": note_path.relative_to(self._vault_root).as_posix(),
            "canonical_hash": canonical_hash,
            "action": action,
            "projection_schema": PROJECTION_SCHEMA_VERSION,
            "source_authority": "MASTER_BRAIN_CANONICAL_STORE",
            "store_id": self._repository.store_id,
            "store_sha256": self._repository.store_sha256,
        }

    def _all_knowledge_ids(self) -> list[str]:
        return self._repository.knowledge_ids

    @staticmethod
    def _log_projection(operation: str, receipt: dict[str, Any]) -> None:
        LOGGER.info(
            "master_brain_projection operation=%s knowledge_id=%s revision=%s status=%s action=%s path=%s",
            operation,
            receipt["knowledge_id"],
            receipt["revision"],
            receipt["canonical_status"],
            receipt["action"],
            receipt["projection_path"],
        )

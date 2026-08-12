"""Fail-honest, read-only retrieval from the Master Brain canonical store.

This module deliberately has no Obsidian, VOX database, BM25, Chroma, or
PostgreSQL dependency. Search reads accepted canonical records directly.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger(__name__)

AUTHORITY_CLASS = "AUTHORITATIVE"
SOURCE_AUTHORITY = "MASTER_BRAIN_CANONICAL_STORE"
SOURCE_TEMPERATURE = "COLD_DEEP"
ALLOWED_STATUSES = {
    "CANDIDATE",
    "CURRENT",
    "SUPERSEDED",
    "REJECTED",
    "CONFLICT",
    "RETIRED",
}
SEARCHABLE_FIELDS = ("title", "summary", "content")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class CanonicalStoreUnavailable(RuntimeError):
    """The configured canonical source cannot satisfy reads."""


class CanonicalStoreInvalid(RuntimeError):
    """The configured canonical source violates the record contract."""


class CanonicalKnowledgeNotFound(LookupError):
    """No requested canonical ID/revision exists."""


class ReadOnlyCanonicalRepository:
    """Validated, immutable-in-process view of canonical JSONL records.

    Loading reads the source once and records its SHA-256. Public responses are
    deep copies so callers cannot mutate the repository view. This class never
    opens any path for writing.
    """

    def __init__(self, store_path: str | os.PathLike[str], *, store_id: str = "master-brain-canonical-v0.1") -> None:
        self._store_path = Path(store_path).expanduser().resolve(strict=False)
        self._store_id = store_id
        self._records: tuple[dict[str, Any], ...] = ()
        self._by_id: dict[str, tuple[dict[str, Any], ...]] = {}
        self._store_sha256 = ""
        self._load()

    @classmethod
    def from_environment(cls) -> "ReadOnlyCanonicalRepository":
        """Create the repository from one explicit/default canonical path."""

        configured = os.getenv("MASTER_BRAIN_CANONICAL_STORE_PATH")
        if configured:
            return cls(configured)
        repository_root = Path(__file__).resolve().parents[1]
        return cls(repository_root / "10_CANONICAL_KNOWLEDGE" / "canonical_records.jsonl")

    @property
    def store_sha256(self) -> str:
        return self._store_sha256

    @property
    def store_id(self) -> str:
        return self._store_id

    @property
    def knowledge_ids(self) -> list[str]:
        """Return all unique knowledge IDs in the store."""
        return list(self._by_id.keys())

    def get(self, knowledge_id: str, *, revision: int | None = None) -> dict[str, Any]:
        """Return an exact historical revision or the single CURRENT revision."""

        normalized_id = self._validate_lookup_id(knowledge_id)
        revisions = self._by_id.get(normalized_id)
        if not revisions:
            raise CanonicalKnowledgeNotFound(f"knowledge_id not found: {normalized_id}")

        if revision is None:
            matches = [record for record in revisions if record["canonical_status"] == "CURRENT"]
            if not matches:
                raise CanonicalKnowledgeNotFound(f"no CURRENT revision for knowledge_id: {normalized_id}")
            record = matches[0]
            retrieval_mode = "current_revision"
        else:
            if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
                raise ValueError("revision must be a positive integer")
            record = next((item for item in revisions if item["revision"] == revision), None)
            if record is None:
                raise CanonicalKnowledgeNotFound(f"revision {revision} not found for knowledge_id: {normalized_id}")
            retrieval_mode = "exact_revision"

        response = self._response(record, retrieval_mode=retrieval_mode)
        self._log_retrieval("get", response)
        return response

    def search(self, query: str, *, include_history: bool = False, limit: int = 10) -> list[dict[str, Any]]:
        """Query canonical text directly, without a derived index.

        This is an intentionally bounded direct-text query, not an embedding or
        vector-semantic claim. Historical records are excluded unless requested.
        """

        if not isinstance(query, str) or not query.strip():
            raise ValueError("query must be non-empty text")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("limit must be an integer from 1 to 100")

        phrase = query.strip().lower()
        tokens = set(TOKEN_PATTERN.findall(phrase))
        scored: list[tuple[int, int, str, dict[str, Any]]] = []
        for record in self._records:
            if not include_history and record["canonical_status"] != "CURRENT":
                continue
            searchable = " ".join(str(record.get(field, "")) for field in SEARCHABLE_FIELDS).lower()
            searchable_tokens = set(TOKEN_PATTERN.findall(searchable))
            score = len(tokens & searchable_tokens)
            if phrase in searchable:
                score += max(2, len(tokens))
            if score:
                scored.append((score, record["revision"], record["knowledge_id"], record))

        scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
        responses = [
            self._response(record, retrieval_mode="direct_canonical_text", query_score=score)
            for score, _, _, record in scored[:limit]
        ]
        for response in responses:
            self._log_retrieval("search", response)
        return responses

    def _load(self) -> None:
        if not self._store_path.is_file():
            raise CanonicalStoreUnavailable(f"canonical store unavailable: {self._store_path}")
        try:
            source_bytes = self._store_path.read_bytes()
        except OSError as exc:
            raise CanonicalStoreUnavailable(f"canonical store unreadable: {self._store_path}") from exc
        if not source_bytes.strip():
            raise CanonicalStoreUnavailable(f"canonical store is empty: {self._store_path}")

        records: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(source_bytes.splitlines(), start=1):
            if not raw_line.strip():
                continue
            try:
                record = json.loads(raw_line)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise CanonicalStoreInvalid(f"invalid JSON at canonical store line {line_number}") from exc
            self._validate_record(record, line_number)
            records.append(record)
        if not records:
            raise CanonicalStoreUnavailable(f"canonical store contains no records: {self._store_path}")

        grouped: dict[str, list[dict[str, Any]]] = {}
        seen_revisions: set[tuple[str, int]] = set()
        for record in records:
            key = (record["knowledge_id"], record["revision"])
            if key in seen_revisions:
                raise CanonicalStoreInvalid(f"duplicate canonical revision: {key[0]} revision {key[1]}")
            seen_revisions.add(key)
            grouped.setdefault(record["knowledge_id"], []).append(record)

        for knowledge_id, revisions in grouped.items():
            revisions.sort(key=lambda item: item["revision"])
            current_count = sum(item["canonical_status"] == "CURRENT" for item in revisions)
            if current_count > 1:
                raise CanonicalStoreInvalid(f"multiple CURRENT revisions for knowledge_id: {knowledge_id}")

        self._records = tuple(deepcopy(records))
        self._by_id = {key: tuple(deepcopy(value)) for key, value in grouped.items()}
        self._store_sha256 = hashlib.sha256(source_bytes).hexdigest()

    @staticmethod
    def _validate_record(record: Any, line_number: int) -> None:
        if not isinstance(record, dict):
            raise CanonicalStoreInvalid(f"canonical store line {line_number} must be an object")
        required = {
            "knowledge_id": str,
            "revision": int,
            "canonical_status": str,
            "title": str,
            "content": str,
            "evidence_ids": list,
        }
        for field, expected_type in required.items():
            value = record.get(field)
            if not isinstance(value, expected_type) or (expected_type is int and isinstance(value, bool)):
                raise CanonicalStoreInvalid(f"line {line_number} has invalid {field}")
        if not record["knowledge_id"].strip() or not record["title"].strip():
            raise CanonicalStoreInvalid(f"line {line_number} has an empty identity/title")
        if record["revision"] < 1:
            raise CanonicalStoreInvalid(f"line {line_number} revision must be positive")
        if record["canonical_status"] not in ALLOWED_STATUSES:
            raise CanonicalStoreInvalid(f"line {line_number} has unsupported canonical_status")
        if not all(isinstance(item, str) and item.strip() for item in record["evidence_ids"]):
            raise CanonicalStoreInvalid(f"line {line_number} has invalid evidence_ids")

    @staticmethod
    def _validate_lookup_id(knowledge_id: str) -> str:
        if not isinstance(knowledge_id, str) or not knowledge_id.strip():
            raise ValueError("knowledge_id must be non-empty text")
        return knowledge_id.strip()

    def _response(self, record: dict[str, Any], *, retrieval_mode: str, query_score: int | None = None) -> dict[str, Any]:
        result = deepcopy(record)
        result["source_authority"] = SOURCE_AUTHORITY
        result["authority_class"] = AUTHORITY_CLASS
        result["source_temperature"] = SOURCE_TEMPERATURE
        result["provenance"] = {"evidence_ids": deepcopy(record["evidence_ids"])}
        result["retrieval_authority"] = {
            "store_id": self._store_id,
            "store_sha256": self._store_sha256,
            "retrieved_from": SOURCE_AUTHORITY,
            "indexed_from": None,
            "retrieval_mode": retrieval_mode,
        }
        if query_score is not None:
            result["query_score"] = query_score
        return result

    @staticmethod
    def _log_retrieval(operation: str, response: dict[str, Any]) -> None:
        LOGGER.info(
            "master_brain_retrieval operation=%s authority=%s store_id=%s knowledge_id=%s revision=%s status=%s",
            operation,
            response["source_authority"],
            response["retrieval_authority"]["store_id"],
            response["knowledge_id"],
            response["revision"],
            response["canonical_status"],
        )

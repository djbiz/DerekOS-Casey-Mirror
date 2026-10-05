"""Durable JSONL storage helpers and structured bulk operation results."""

from __future__ import annotations

import contextlib
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator


class StorageError(RuntimeError):
    """A JSONL storage operation failed."""


class PathConfinementError(StorageError):
    """A path escaped its allowed root."""


@dataclass(frozen=True)
class ItemFailure:
    identifier: str
    error_type: str
    message: str


@dataclass
class BulkResult:
    """Structured best-effort result, while remaining list-like for receipts."""

    operation: str
    successes: list[dict[str, Any]] = field(default_factory=list)
    failures: list[dict[str, Any]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    @property
    def status(self) -> str:
        if self.failures and self.successes:
            return "partial"
        if self.failures:
            return "failed"
        return "success"

    def add_success(self, item: dict[str, Any]) -> None:
        self.successes.append(item)

    def add_failure(self, identifier: Any, exc: BaseException) -> None:
        self.failures.append({
            "identifier": str(identifier),
            "error_type": type(exc).__name__,
            "message": str(exc),
        })

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "status": self.status,
            "success_count": len(self.successes),
            "failure_count": len(self.failures),
            "successes": self.successes,
            "failures": self.failures,
        }

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.successes)

    def __len__(self) -> int:
        return len(self.successes)

    def __getitem__(self, index: int) -> dict[str, Any]:
        return self.successes[index]


def ensure_relative_to(path: str | os.PathLike[str], root: str | os.PathLike[str]) -> Path:
    resolved = Path(path).expanduser().resolve(strict=False)
    allowed_root = Path(root).expanduser().resolve(strict=False)
    try:
        resolved.relative_to(allowed_root)
    except ValueError as exc:
        raise PathConfinementError(f"path escapes allowed root: {resolved}") from exc
    return resolved


def read_jsonl(path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    jsonl_path = Path(path).expanduser().resolve(strict=False)
    if not jsonl_path.is_file():
        return []
    try:
        source_bytes = jsonl_path.read_bytes()
    except OSError as exc:
        raise StorageError(f"jsonl file unreadable: {jsonl_path}") from exc
    if not source_bytes.strip():
        return []
    records: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(source_bytes.splitlines(), start=1):
        if not raw_line.strip():
            continue
        try:
            record = json.loads(raw_line)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise StorageError(f"invalid JSON at {jsonl_path} line {line_number}") from exc
        if not isinstance(record, dict):
            raise StorageError(f"jsonl line {line_number} must be an object")
        records.append(record)
    return records


@contextlib.contextmanager
def _file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+b") as lock_file:
        if os.name == "nt":  # pragma: no cover - exercised on Windows only
            import msvcrt
            msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def append_jsonl(path: str | os.PathLike[str], record: dict[str, Any]) -> None:
    if not isinstance(record, dict):
        raise StorageError("jsonl records must be objects")
    jsonl_path = Path(path).expanduser().resolve(strict=False)
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = jsonl_path.with_suffix(jsonl_path.suffix + ".lock")
    line = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    with _file_lock(lock_path):
        with open(jsonl_path, "a", encoding="utf-8", newline="\n") as output:
            output.write(line)
            output.flush()
            os.fsync(output.fileno())

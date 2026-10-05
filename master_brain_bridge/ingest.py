"""Authoritative deterministic Phase 1 ChatGPT export ingest."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import RuntimeConfig

INGEST_VERSION = "1.1.0"
_SOURCE_PATTERN = re.compile(r"^conversations-[0-9]{3}\.json$")
_SRCMSG_PATTERN = re.compile(r"^srcmsg_[a-f0-9]{32}$")
_SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")


class IngestError(RuntimeError):
    """Ingest could not complete safely."""


@dataclass(frozen=True)
class IngestReport:
    status: str
    source_files_processed: list[str]
    total_conversations: int
    total_messages_written: int
    duplicate_conversation_ids: list[dict[str, str]]
    anomalous_conversations: list[str]
    duplicate_source_record_ids: list[str]
    messages_sha256: str
    output_dir: str
    index_dir: str

    @property
    def ok(self) -> bool:
        return self.status == "PASS"

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(source_file: str, conversation_id: str, message_id: str) -> str:
    value = f"{source_file}\x1f{conversation_id}\x1f{message_id}".encode("utf-8")
    return f"srcmsg_{hashlib.sha256(value).hexdigest()[:32]}"


def _atomic_replace(temporary: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(6):
        try:
            temporary.replace(destination)
            return
        except PermissionError:
            if destination.exists() and _sha256(temporary) == _sha256(destination):
                temporary.unlink()
                return
            if attempt == 5:
                raise
            time.sleep(0.1 * (attempt + 1))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _iso(ts: float | None) -> str | None:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()
    except (OSError, OverflowError, ValueError):
        return f"UNPARSEABLE_RAW:{ts!r}"


def _joined_text(message: dict[str, Any]) -> str:
    content = message.get("content") or {}
    content_type = content.get("content_type")
    if content_type in ("text", "multimodal_text"):
        parts = content.get("parts")
        if not isinstance(parts, list):
            return ""
        return "\n".join(p for p in parts if isinstance(p, str))
    if content_type == "reasoning_recap":
        recap = content.get("content")
        return recap if isinstance(recap, str) else ""
    if content_type == "thoughts":
        thoughts = content.get("thoughts")
        if not isinstance(thoughts, list):
            return ""
        return "\n\n".join(
            t.get("content", "")
            for t in thoughts
            if isinstance(t, dict) and isinstance(t.get("content"), str)
        )
    return ""


def _linear_path(mapping: dict[str, Any], current_node: str | None) -> list[str]:
    if not current_node or current_node not in mapping:
        return []
    path: list[str] = []
    node_id: str | None = current_node
    seen: set[str] = set()
    while node_id is not None:
        if node_id in seen:
            break
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id)
        if node is None:
            break
        node_id = node.get("parent")
    path.reverse()
    return path


def _process_conversation(conv: dict[str, Any], source_file: str, source_sha256: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    conversation_id = conv.get("conversation_id") or conv.get("id")
    title = conv.get("title")
    mapping = conv.get("mapping") or {}
    if not isinstance(mapping, dict):
        mapping = {}
    current_node = conv.get("current_node")

    main_path = _linear_path(mapping, current_node)
    main_path_set = set(main_path)
    main_index = {node_id: idx for idx, node_id in enumerate(main_path)}

    records: list[dict[str, Any]] = []
    message_count = 0
    unparseable_timestamps = 0
    child_ids: dict[str, list[str]] = {node_id: [] for node_id in mapping}
    for child_id, child_node in mapping.items():
        if isinstance(child_node, dict) and child_node.get("parent") in mapping:
            child_ids[child_node["parent"]].append(child_id)
    for children in child_ids.values():
        children.sort()

    for node_id in sorted(mapping):
        node = mapping[node_id]
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not message:
            continue
        message_count += 1
        author = message.get("author") or {}
        timestamp = _iso(message.get("create_time"))
        if timestamp is not None and timestamp.startswith("UNPARSEABLE_RAW:"):
            unparseable_timestamps += 1
        record = {
            "source_record_id": _stable_id(source_file, str(conversation_id), str(message.get("id") or node_id)),
            "message_id": str(message.get("id") or node_id),
            "node_id": str(node_id),
            "conversation_id": str(conversation_id),
            "conversation_title": title,
            "source_file": source_file,
            "role": author.get("role"),
            "author_name": author.get("name"),
            "timestamp": timestamp,
            "text": _joined_text(message),
            "content_type": (message.get("content") or {}).get("content_type"),
            "branch": "main" if node_id in main_path_set else "alternate",
            "sequence_index": main_index.get(node_id),
            "parent_message_id": node.get("parent"),
            "child_message_ids": child_ids.get(node_id, []),
            "source_sha256": source_sha256,
            "ingest_version": INGEST_VERSION,
        }
        records.append(record)

    anomalous = current_node is not None and not main_path
    conv_record = {
        "conversation_id": str(conversation_id),
        "title": title,
        "source_file": source_file,
        "create_time": _iso(conv.get("create_time")),
        "update_time": _iso(conv.get("update_time")),
        "message_count_total": message_count,
        "message_count_main_path": len(main_path),
        "message_count_alternate": message_count - len(main_path),
        "anomalous_current_node": anomalous,
        "unparseable_timestamps": unparseable_timestamps,
        "mapping_node_count": len(mapping),
        "structural_node_count": len(mapping) - message_count,
    }
    return records, conv_record


def validate_message_record(record: dict[str, Any], *, context: str = "record") -> None:
    required = {
        "source_record_id", "message_id", "node_id", "conversation_id", "conversation_title",
        "source_file", "role", "author_name", "timestamp", "text", "content_type",
        "branch", "sequence_index", "parent_message_id", "child_message_ids", "source_sha256", "ingest_version",
    }
    extra = set(record) - required
    missing = required - set(record)
    if missing or extra:
        raise IngestError(f"{context} schema keys invalid missing={sorted(missing)} extra={sorted(extra)}")
    if not isinstance(record["source_record_id"], str) or not _SRCMSG_PATTERN.fullmatch(record["source_record_id"]):
        raise IngestError(f"{context} invalid source_record_id")
    for field in ("message_id", "node_id", "conversation_id"):
        if not isinstance(record[field], str) or not record[field]:
            raise IngestError(f"{context} invalid {field}")
    if record["conversation_title"] is not None and not isinstance(record["conversation_title"], str):
        raise IngestError(f"{context} invalid conversation_title")
    if not isinstance(record["source_file"], str) or not _SOURCE_PATTERN.fullmatch(record["source_file"]):
        raise IngestError(f"{context} invalid source_file")
    for field in ("role", "author_name", "timestamp", "content_type", "parent_message_id"):
        if record[field] is not None and not isinstance(record[field], str):
            raise IngestError(f"{context} invalid {field}")
    if not isinstance(record["text"], str):
        raise IngestError(f"{context} invalid text")
    if record["branch"] not in {"main", "alternate"}:
        raise IngestError(f"{context} invalid branch")
    if record["sequence_index"] is not None and (not isinstance(record["sequence_index"], int) or isinstance(record["sequence_index"], bool) or record["sequence_index"] < 0):
        raise IngestError(f"{context} invalid sequence_index")
    if not isinstance(record["child_message_ids"], list) or not all(isinstance(item, str) for item in record["child_message_ids"]):
        raise IngestError(f"{context} invalid child_message_ids")
    if len(record["child_message_ids"]) != len(set(record["child_message_ids"])):
        raise IngestError(f"{context} duplicate child_message_ids")
    if not isinstance(record["source_sha256"], str) or not _SHA_PATTERN.fullmatch(record["source_sha256"]):
        raise IngestError(f"{context} invalid source_sha256")
    if record["ingest_version"] != INGEST_VERSION:
        raise IngestError(f"{context} invalid ingest_version")


def _validate_messages_file(path: Path) -> None:
    seen: set[str] = set()
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IngestError(f"invalid JSON in staged messages line {line_number}") from exc
            if not isinstance(record, dict):
                raise IngestError(f"staged messages line {line_number} must be object")
            validate_message_record(record, context=f"staged messages line {line_number}")
            if record["source_record_id"] in seen:
                raise IngestError(f"duplicate source_record_id in staged messages: {record['source_record_id']}")
            seen.add(record["source_record_id"])


def _build(source_dir: Path, output_stage: Path, index_stage: Path) -> IngestReport:
    source_files = sorted(source_dir.glob("conversations-*.json"))
    source_files = [path for path in source_files if _SOURCE_PATTERN.fullmatch(path.name)]
    if not source_files:
        raise IngestError(f"No conversations-*.json found under {source_dir}")

    all_conversations: list[dict[str, Any]] = []
    seen_conversation_ids: dict[str, str] = {}
    duplicate_conversation_ids: list[dict[str, str]] = []
    total_messages_written = 0
    anomalous_conversations: list[str] = []
    manifest_files: list[dict[str, Any]] = []
    source_record_ids: set[str] = set()
    duplicate_source_record_ids: list[str] = []
    mapping_nodes = 0
    structural_nodes = 0

    output_stage.mkdir(parents=True, exist_ok=True)
    index_stage.mkdir(parents=True, exist_ok=True)
    messages_path = output_stage / "messages.jsonl"
    with messages_path.open("w", encoding="utf-8", newline="\n") as messages_out:
        for source_path in source_files:
            source_file = source_path.name
            source_sha256 = _sha256(source_path)
            try:
                conversations = json.loads(source_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                raise IngestError(f"invalid JSON source file: {source_file}") from exc
            if not isinstance(conversations, list):
                raise IngestError(f"source file must contain a list: {source_file}")

            file_conversation_count = 0
            file_message_count = 0
            file_mapping_nodes = 0
            for conv in conversations:
                if not isinstance(conv, dict):
                    raise IngestError(f"conversation in {source_file} must be an object")
                records, conv_record = _process_conversation(conv, source_file, source_sha256)
                mapping_nodes += conv_record["mapping_node_count"]
                structural_nodes += conv_record["structural_node_count"]
                file_mapping_nodes += conv_record["mapping_node_count"]
                file_conversation_count += 1
                file_message_count += conv_record["message_count_total"]

                cid = conv_record["conversation_id"]
                if cid in seen_conversation_ids:
                    duplicate_conversation_ids.append({"conversation_id": cid, "first_seen_in": seen_conversation_ids[cid], "also_seen_in": source_file})
                else:
                    seen_conversation_ids[cid] = source_file
                if conv_record["anomalous_current_node"]:
                    anomalous_conversations.append(cid)
                all_conversations.append(conv_record)

                for record in records:
                    validate_message_record(record, context=f"{source_file}:{record['node_id']}")
                    record_id = record["source_record_id"]
                    if record_id in source_record_ids:
                        duplicate_source_record_ids.append(record_id)
                    source_record_ids.add(record_id)
                    messages_out.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                    messages_out.write("\n")
                    total_messages_written += 1
            manifest_files.append({
                "filename": source_file,
                "size_bytes": source_path.stat().st_size,
                "sha256": source_sha256,
                "conversation_count": file_conversation_count,
                "message_count": file_message_count,
                "mapping_node_count": file_mapping_nodes,
                "json_valid": True,
            })
        messages_out.flush()
        os.fsync(messages_out.fileno())

    _validate_messages_file(messages_path)
    _write_json(output_stage / "conversations_index.json", all_conversations)
    total_unparseable_timestamps = sum(c["unparseable_timestamps"] for c in all_conversations)
    status = "PASS" if not duplicate_conversation_ids and not anomalous_conversations and not duplicate_source_record_ids else "FAIL"
    report_dict = {
        "ingest_version": INGEST_VERSION,
        "status": status,
        "source_files_processed": [p.name for p in source_files],
        "total_conversations": len(all_conversations),
        "total_messages_written": total_messages_written,
        "duplicate_conversation_ids": duplicate_conversation_ids,
        "anomalous_conversations": anomalous_conversations,
        "total_unparseable_timestamps": total_unparseable_timestamps,
        "mapping_nodes": mapping_nodes,
        "structural_nodes_without_messages": structural_nodes,
        "duplicate_source_record_ids": duplicate_source_record_ids,
        "messages_sha256": _sha256(messages_path),
    }
    _write_json(output_stage / "ingest_report.json", report_dict)
    _write_json(index_stage / "source_manifest.json", {
        "schema_version": "1.0.0",
        "corpus": "operator-supplied-chatgpt-export",
        "files": manifest_files,
        "totals": {
            "source_files": len(source_files),
            "conversations": len(all_conversations),
            "mapping_nodes": mapping_nodes,
            "messages": total_messages_written,
            "structural_nodes_without_messages": structural_nodes,
        },
    })
    _write_json(output_stage / "checkpoint.json", {
        "ingest_version": INGEST_VERSION,
        "completed_source_files": [p.name for p in source_files],
        "messages_sha256": report_dict["messages_sha256"],
        "status": status,
    })
    return IngestReport(
        status=status,
        source_files_processed=report_dict["source_files_processed"],
        total_conversations=len(all_conversations),
        total_messages_written=total_messages_written,
        duplicate_conversation_ids=duplicate_conversation_ids,
        anomalous_conversations=anomalous_conversations,
        duplicate_source_record_ids=duplicate_source_record_ids,
        messages_sha256=report_dict["messages_sha256"],
        output_dir="",
        index_dir="",
    )


def _promote(staged_output: Path, output_dir: Path, staged_index: Path, index_dir: Path) -> None:
    for name in ("messages.jsonl", "conversations_index.json", "ingest_report.json", "checkpoint.json"):
        _atomic_replace(staged_output / name, output_dir / name)
    _atomic_replace(staged_index / "source_manifest.json", index_dir / "source_manifest.json")


def run_ingest(
    source_dir: str | os.PathLike[str] | None = None,
    output_dir: str | os.PathLike[str] | None = None,
    index_dir: str | os.PathLike[str] | None = None,
) -> IngestReport:
    """Generate deterministic Phase 1 artifacts through staged validation and safe promotion."""

    config = RuntimeConfig.load()
    source = Path(source_dir).expanduser().resolve(strict=False) if source_dir is not None else config.raw_chatgpt_dir
    output = Path(output_dir).expanduser().resolve(strict=False) if output_dir is not None else config.ingest_output_dir
    index = Path(index_dir).expanduser().resolve(strict=False) if index_dir is not None else config.source_index_dir
    if not source.is_dir():
        raise IngestError(f"source directory unavailable: {source}")
    output.parent.mkdir(parents=True, exist_ok=True)
    index.parent.mkdir(parents=True, exist_ok=True)
    staging_parent = output.parent
    stage_root = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=staging_parent))
    staged_output = stage_root / "output"
    staged_index = stage_root / "index"
    try:
        report = _build(source, staged_output, staged_index)
        _promote(staged_output, output, staged_index, index)
        return IngestReport(**{**report.to_dict(), "output_dir": str(output), "index_dir": str(index)})
    finally:
        shutil.rmtree(stage_root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="DerekOS Master Brain Phase 1 ingest")
    parser.add_argument("--source-dir", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--index-dir", type=Path, default=None)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)
    try:
        report = run_ingest(args.source_dir, args.output_dir, args.index_dir)
    except IngestError as exc:
        if args.json_output:
            print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        else:
            print(f"ingest failed: {exc}")
        return 1
    if args.json_output:
        print(json.dumps(report.to_dict(), sort_keys=True))
    else:
        print(f"conversations: {report.total_conversations}")
        print(f"messages written: {report.total_messages_written}")
        print(f"duplicate conversation_ids: {len(report.duplicate_conversation_ids)}")
        print(f"anomalous conversations (bad current_node): {len(report.anomalous_conversations)}")
        print(f"wrote output: {report.output_dir}")
        print(f"wrote index: {report.index_dir}")
    return 0 if report.ok else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

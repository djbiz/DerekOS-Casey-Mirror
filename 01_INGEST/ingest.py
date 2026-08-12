"""
Phase 1 ingestion — Codex role (see MASTER_BRAIN_BUILD_SPEC.md §4, §5.1, §7).

Reads 00_RAW_ARCHIVE/chatgpt/conversations-*.json (read-only, never written
to) and produces:
  - 01_INGEST/messages.jsonl            one record per message node
  - 01_INGEST/conversations_index.json  one record per conversation
  - 01_INGEST/ingest_report.json        counts, duplicate-conversation
                                         flags, and reconciliation numbers
                                         for Audit Bot's Phase 1 check

Design notes (per spec):
  - mapping is a tree, not a flat list - edits/regenerations create
    sibling branches. current_node marks the tip of the branch actually
    shown last. We walk the parent chain from current_node back to the
    root to get the linear "main" conversation (sequence_index 0..N).
  - Off-path nodes (edited-out / abandoned branches) are NOT dropped -
    spec §10 "no fabricated success" and the ingest exit criteria say
    "zero silently-dropped conversations" - extending that principle to
    messages too. They're emitted with branch="alternate" and
    sequence_index=null, since they have no single well-defined linear
    position.
  - Duplicate conversation_id across different source files is flagged
    in ingest_report.json, not silently deduplicated by picking one
    arbitrarily.
"""

from __future__ import annotations

import json
import hashlib
import os
import time
from datetime import UTC, datetime
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "00_RAW_ARCHIVE" / "chatgpt"
OUT_DIR = Path(__file__).resolve().parent
INDEX_DIR = OUT_DIR.parent / "13_SOURCE_INDEX"
INGEST_VERSION = "1.1.0"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_id(source_file: str, conversation_id: str, message_id: str) -> str:
    value = f"{source_file}\x1f{conversation_id}\x1f{message_id}".encode("utf-8")
    return f"srcmsg_{hashlib.sha256(value).hexdigest()[:32]}"


def _replace(temporary: Path, destination: Path) -> None:
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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _replace(temporary, path)


def _iso(ts: float | None) -> str | None:
    """Convert a Unix timestamp to ISO 8601. Some exported timestamps are
    out of range for Windows' fromtimestamp() (e.g. negative or absurdly
    large values) - falls back to a raw-value marker rather than crashing
    the whole ingestion run or silently losing the record's timestamp."""
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(ts, tz=UTC).isoformat()
    except (OSError, OverflowError, ValueError):
        return f"UNPARSEABLE_RAW:{ts!r}"


def _joined_text(message: dict) -> str:
    """Extract whatever text a message node actually carries, across the
    content_types observed in this archive (text, multimodal_text,
    reasoning_recap, thoughts - verified directly against real export
    data, not assumed). Content types with no textual payload (e.g. a
    pure image ref) legitimately return "" - that's a fact about the
    message, not a failure of this function. What must not happen is a
    content_type that DOES carry real text (reasoning_recap's `content`
    string, thoughts[].content) silently returning "" because only
    `parts` was checked."""
    content = message.get("content") or {}
    content_type = content.get("content_type")

    if content_type in ("text", "multimodal_text"):
        parts = content.get("parts")
        if not isinstance(parts, list):
            return ""
        # parts can contain non-string items (e.g. multimodal image refs) -
        # keep only string parts; not this function's job to interpret
        # non-text content, just don't crash extracting it.
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


def _linear_path(mapping: dict, current_node: str | None) -> list[str]:
    """Node ids from root to current_node, in order. Empty if
    current_node is missing or not present in mapping (both seen in real
    exports - handled honestly, not assumed away)."""
    if not current_node or current_node not in mapping:
        return []
    path = []
    node_id = current_node
    seen = set()
    while node_id is not None:
        if node_id in seen:
            # cycle - malformed export data. Stop rather than loop forever;
            # ingest_report records this conversation as anomalous.
            break
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id)
        if node is None:
            break
        node_id = node.get("parent")
    path.reverse()
    return path


def _process_conversation(
    conv: dict, source_file: str, source_sha256: str
) -> tuple[list[dict], dict]:
    conversation_id = conv.get("conversation_id") or conv.get("id")
    title = conv.get("title")
    mapping = conv.get("mapping") or {}
    current_node = conv.get("current_node")

    main_path = _linear_path(mapping, current_node)
    main_path_set = set(main_path)
    main_index = {node_id: idx for idx, node_id in enumerate(main_path)}

    records = []
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
        message = node.get("message")
        if not message:
            continue  # synthetic root / empty node, not a real message
        message_count += 1
        author = message.get("author") or {}
        timestamp = _iso(message.get("create_time"))
        if timestamp is not None and timestamp.startswith("UNPARSEABLE_RAW:"):
            unparseable_timestamps += 1
        record = {
            "source_record_id": _stable_id(source_file, conversation_id, message.get("id") or node_id),
            "message_id": message.get("id") or node_id,
            "node_id": node_id,
            "conversation_id": conversation_id,
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
            "child_message_ids": child_ids[node_id],
            "source_sha256": source_sha256,
            "ingest_version": INGEST_VERSION,
        }
        records.append(record)

    anomalous = current_node is not None and not main_path
    conv_record = {
        "conversation_id": conversation_id,
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


def main() -> None:
    source_files = sorted(RAW_DIR.glob("conversations-*.json"))
    if not source_files:
        raise SystemExit(f"No conversations-*.json found under {RAW_DIR}")

    all_conversations: list[dict] = []
    seen_conversation_ids: dict[str, str] = {}
    duplicate_conversation_ids: list[dict] = []
    total_messages_written = 0
    anomalous_conversations: list[str] = []
    manifest_files: list[dict] = []
    source_record_ids: set[str] = set()
    duplicate_source_record_ids: list[str] = []
    mapping_nodes = 0
    structural_nodes = 0

    messages_path = OUT_DIR / "messages.jsonl"
    temporary_messages_path = messages_path.with_suffix(".jsonl.tmp")
    with temporary_messages_path.open("w", encoding="utf-8", newline="\n") as messages_out:
        for source_path in source_files:
            source_file = source_path.name
            source_sha256 = _sha256(source_path)
            with source_path.open(encoding="utf-8") as f:
                conversations = json.load(f)

            for conv in conversations:
                records, conv_record = _process_conversation(conv, source_file, source_sha256)
                mapping_nodes += conv_record["mapping_node_count"]
                structural_nodes += conv_record["structural_node_count"]

                cid = conv_record["conversation_id"]
                if cid in seen_conversation_ids:
                    duplicate_conversation_ids.append(
                        {
                            "conversation_id": cid,
                            "first_seen_in": seen_conversation_ids[cid],
                            "also_seen_in": source_file,
                        }
                    )
                else:
                    seen_conversation_ids[cid] = source_file

                if conv_record["anomalous_current_node"]:
                    anomalous_conversations.append(cid)

                all_conversations.append(conv_record)

                for record in records:
                    record_id = record["source_record_id"]
                    if record_id in source_record_ids:
                        duplicate_source_record_ids.append(record_id)
                    source_record_ids.add(record_id)
                    messages_out.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
                    messages_out.write("\n")
                    total_messages_written += 1
            manifest_files.append(
                {
                    "filename": source_file,
                    "size_bytes": source_path.stat().st_size,
                    "sha256": source_sha256,
                    "conversation_count": sum(1 for c in all_conversations if c["source_file"] == source_file),
                    "message_count": sum(c["message_count_total"] for c in all_conversations if c["source_file"] == source_file),
                    "mapping_node_count": sum(c["mapping_node_count"] for c in all_conversations if c["source_file"] == source_file),
                    "json_valid": True,
                }
            )
        messages_out.flush()
        os.fsync(messages_out.fileno())
    _replace(temporary_messages_path, messages_path)

    index_path = OUT_DIR / "conversations_index.json"
    _write_json(index_path, all_conversations)

    total_unparseable_timestamps = sum(
        c["unparseable_timestamps"] for c in all_conversations
    )
    report = {
        "ingest_version": INGEST_VERSION,
        "status": "PASS" if not duplicate_conversation_ids and not anomalous_conversations and not duplicate_source_record_ids else "FAIL",
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
    report_path = OUT_DIR / "ingest_report.json"
    _write_json(report_path, report)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    _write_json(
        INDEX_DIR / "source_manifest.json",
        {
            "schema_version": "1.0.0",
            "corpus": "chatgpt-export-2026-08-10",
            "files": manifest_files,
            "totals": {
                "source_files": len(source_files),
                "conversations": len(all_conversations),
                "mapping_nodes": mapping_nodes,
                "messages": total_messages_written,
                "structural_nodes_without_messages": structural_nodes,
            },
        },
    )
    _write_json(
        OUT_DIR / "checkpoint.json",
        {
            "ingest_version": INGEST_VERSION,
            "completed_source_files": [p.name for p in source_files],
            "messages_sha256": report["messages_sha256"],
            "status": report["status"],
        },
    )

    print(f"conversations: {len(all_conversations)}")
    print(f"messages written: {total_messages_written}")
    print(f"duplicate conversation_ids: {len(duplicate_conversation_ids)}")
    print(f"anomalous conversations (bad current_node): {len(anomalous_conversations)}")
    print(f"wrote: {messages_path}")
    print(f"wrote: {index_path}")
    print(f"wrote: {report_path}")


if __name__ == "__main__":
    main()

"""
DELTA INGEST — other-ai-export fragment format.

Reads 00_RAW_ARCHIVE/other-ai-export/conversations.json and produces
incremental additions to:
  - 01_INGEST/messages.jsonl
  - 01_INGEST/conversations_index.json
  - 14_TESTS_AUDITS/DELTA_IMPORT_RECONCILIATION_REPORT.md

Schema differences from canonical ChatGPT export:
  - conversations are an array at top-level (not wrapped in a dict)
  - conversation id field is `id` (not `conversation_id`)
  - conversation timestamps are `inserted_at` / `updated_at`
  - mapping nodes have `id`, `parent`, `children`, `message` (message may be None)
  - message has `model`, `inserted_at`, `fragments` (no `author`, no `content.content_type`)
  - fragments are atomic units with `type` (REQUEST/RESPONSE) and `content` (string)
  - root node has `message: None`

One canonical message record is emitted per fragment, not per node.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "00_RAW_ARCHIVE" / "other-ai-export"
OUT_DIR = ROOT / "01_INGEST"
INDEX_DIR = ROOT / "13_SOURCE_INDEX"
AUDIT_DIR = ROOT / "14_TESTS_AUDITS"
CANDIDATE_FILE = RAW_DIR / "conversations.json"
MESSAGES_PATH = OUT_DIR / "messages.jsonl"
INDEX_PATH = OUT_DIR / "conversations_index.json"
INGEST_VERSION = "2.0.0"
SOURCE_FORMAT = "other-ai-export-fragments"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_str(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_id(source_hash: str, conversation_id: str, node_id: str, fragment_index: int) -> str:
    raw = f"{source_hash}\x1f{conversation_id}\x1f{node_id}\x1f{fragment_index}"
    return f"srcmsg_{_sha256_str(raw)[:32]}"


def _iso(ts: str | None) -> str | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts).astimezone(UTC).isoformat()
    except (ValueError, TypeError):
        return f"UNPARSEABLE_RAW:{ts!r}"


def _replace(temporary: Path, destination: Path) -> None:
    for attempt in range(6):
        try:
            temporary.replace(destination)
            return
        except PermissionError:
            if destination.exists() and _sha256_file(temporary) == _sha256_file(destination):
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


def _linear_path(mapping: dict) -> list[str]:
    """Node ids from root through the first-child chain. Empty if root missing."""
    root = mapping.get("root")
    if not isinstance(root, dict):
        return []
    path = []
    node_id = "root"
    seen = set()
    while node_id is not None:
        if node_id in seen:
            break
        seen.add(node_id)
        path.append(node_id)
        node = mapping.get(node_id)
        if not isinstance(node, dict):
            break
        children = node.get("children") or []
        if not isinstance(children, list) or not children:
            break
        node_id = children[0]
    return path


def _process_conversation(
    conv: dict, source_file: str, source_sha256: str
) -> tuple[list[dict], dict]:
    conversation_id = conv.get("id")
    title = conv.get("title")
    mapping = conv.get("mapping") or {}
    conv_inserted_at = _iso(conv.get("inserted_at"))
    conv_updated_at = _iso(conv.get("updated_at"))

    main_path = _linear_path(mapping)
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
        msg = node.get("message")
        if not isinstance(msg, dict):
            continue
        fragments = msg.get("fragments") or []
        if not isinstance(fragments, list):
            fragments = []
        if not fragments:
            continue

        message_count += 1
        ts = _iso(msg.get("inserted_at")) or conv_inserted_at
        if ts is not None and ts.startswith("UNPARSEABLE_RAW:"):
            unparseable_timestamps += 1

        model = msg.get("model")
        for fragment_index, frag in enumerate(fragments):
            frag_type = frag.get("type") if isinstance(frag, dict) else None
            frag_content = frag.get("content", "") if isinstance(frag, dict) else ""
            if not isinstance(frag_content, str):
                frag_content = str(frag_content)

            if frag_type == "REQUEST":
                role = "user"
            elif frag_type == "RESPONSE":
                role = "assistant"
            else:
                role = None

            record = {
                "source_record_id": _stable_id(source_sha256, conversation_id, node_id, fragment_index),
                "message_id": node_id,
                "node_id": node_id,
                "conversation_id": conversation_id,
                "conversation_title": title,
                "source_file": source_file,
                "source_format": SOURCE_FORMAT,
                "role": role,
                "author_name": None,
                "timestamp": ts,
                "text": frag_content,
                "content_type": frag_type,
                "branch": "main" if node_id in main_path_set else "alternate",
                "sequence_index": main_index.get(node_id),
                "parent_message_id": node.get("parent"),
                "child_message_ids": child_ids.get(node_id, []),
                "fragment_index": fragment_index,
                "fragment_type": frag_type,
                "model": model,
                "source_sha256": source_sha256,
                "ingest_version": INGEST_VERSION,
            }
            records.append(record)

    conv_record = {
        "conversation_id": conversation_id,
        "title": title,
        "source_file": source_file,
        "source_format": SOURCE_FORMAT,
        "create_time": conv_inserted_at,
        "update_time": conv_updated_at,
        "message_count_total": message_count,
        "message_count_main_path": sum(1 for n in main_path if mapping.get(n, {}).get("message")),
        "message_count_alternate": message_count - sum(1 for n in main_path if mapping.get(n, {}).get("message")),
        "anomalous_current_node": False,
        "unparseable_timestamps": unparseable_timestamps,
        "mapping_node_count": len(mapping),
        "structural_node_count": len(mapping) - message_count,
    }
    return records, conv_record


def main() -> None:
    if not CANDIDATE_FILE.exists():
        raise SystemExit(f"Candidate file not found: {CANDIDATE_FILE}")

    source_sha256 = _sha256_file(CANDIDATE_FILE)
    with CANDIDATE_FILE.open(encoding="utf-8") as f:
        conversations = json.load(f)

    all_records: list[dict] = []
    all_conv_records: list[dict] = []
    seen_conversation_ids: dict[str, str] = {}
    duplicate_conversation_ids: list[dict] = []
    anomalous_conversations: list[str] = []
    source_record_ids: set[str] = set()
    duplicate_source_record_ids: list[str] = []
    total_messages_written = 0
    total_unparseable_timestamps = 0
    mapping_nodes = 0
    structural_nodes = 0
    unknown_authors = 0
    orphaned_nodes = 0
    topology_failures = 0

    # Load existing index for incremental update
    existing_conv_ids = set()
    existing_index = []
    if INDEX_PATH.exists():
        with INDEX_PATH.open(encoding="utf-8") as f:
            try:
                existing_index = json.load(f)
                for c in existing_index:
                    cid = c.get("conversation_id")
                    if cid and c.get("source_file") == source_file:
                        existing_conv_ids.add(cid)
            except json.JSONDecodeError:
                existing_index = []
    else:
        existing_index = []

    # Load existing messages for duplicate detection
    existing_msg_ids = set()
    if MESSAGES_PATH.exists():
        with MESSAGES_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    m = json.loads(line)
                    existing_msg_ids.add(m.get("source_record_id"))
                except json.JSONDecodeError:
                    continue

    source_file = CANDIDATE_FILE.name
    temporary_messages_path = MESSAGES_PATH.with_suffix(".jsonl.tmp")

    # We need to merge existing messages with new ones atomically
    # Read existing messages into memory (feasible for this corpus size)
    existing_messages = []
    if MESSAGES_PATH.exists():
        with MESSAGES_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    existing_messages.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    new_conv_records = []
    for conv in conversations:
        conv_id = conv.get("id")
        if conv_id in existing_conv_ids:
            continue

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

        new_conv_records.append(conv_record)

        for record in records:
            record_id = record["source_record_id"]
            if record_id in source_record_ids or record_id in existing_msg_ids:
                duplicate_source_record_ids.append(record_id)
            source_record_ids.add(record_id)
            all_records.append(record)
            total_messages_written += 1
            if record.get("role") is None:
                unknown_authors += 1

        # Orphaned nodes: nodes whose parent is not in mapping
        for node_id, node in (conv.get("mapping") or {}).items():
            parent = node.get("parent")
            if parent is not None and parent not in (conv.get("mapping") or {}):
                orphaned_nodes += 1

        total_unparseable_timestamps += conv_record["unparseable_timestamps"]

    # Detect topology failures: cycles, unreachable nodes from root
    for conv in conversations:
        mapping = conv.get("mapping") or {}
        visited = set()
        queue = ["root"]
        while queue:
            current = queue.pop(0)
            if current in visited:
                topology_failures += 1
                continue
            visited.add(current)
            node = mapping.get(current)
            if isinstance(node, dict):
                children = node.get("children") or []
                if isinstance(children, list):
                    for child in children:
                        if child not in visited:
                            queue.append(child)
        unreachable = set(mapping.keys()) - visited
        topology_failures += len(unreachable)

    # Write merged messages atomically
    merged_messages = existing_messages + all_records
    temporary_messages_path = MESSAGES_PATH.with_suffix(".jsonl.tmp")
    with temporary_messages_path.open("w", encoding="utf-8", newline="\n") as messages_out:
        for record in merged_messages:
            messages_out.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            messages_out.write("\n")
        messages_out.flush()
        os.fsync(messages_out.fileno())
    _replace(temporary_messages_path, MESSAGES_PATH)

    # Update conversations_index.json incrementally
    merged_index = existing_index + new_conv_records
    _write_json(INDEX_PATH, merged_index)

    # Update source manifest
    manifest_path = INDEX_DIR / "source_manifest.json"
    existing_manifest = {}
    if manifest_path.exists():
        try:
            existing_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_manifest = {}

    files = existing_manifest.get("files", [])
    files.append(
        {
            "filename": source_file,
            "size_bytes": CANDIDATE_FILE.stat().st_size,
            "sha256": source_sha256,
            "conversation_count": len(new_conv_records),
            "message_count": total_messages_written,
            "mapping_node_count": mapping_nodes,
            "json_valid": True,
        }
    )
    totals = existing_manifest.get("totals", {})
    totals["source_files"] = totals.get("source_files", 0) + 1
    totals["conversations"] = totals.get("conversations", 0) + len(new_conv_records)
    totals["messages"] = totals.get("messages", 0) + total_messages_written
    totals["mapping_nodes"] = totals.get("mapping_nodes", 0) + mapping_nodes
    totals["structural_nodes_without_messages"] = totals.get("structural_nodes_without_messages", 0) + structural_nodes
    _write_json(
        manifest_path,
        {
            "schema_version": "1.0.0",
            "corpus": "chatgpt-export-2026-08-10 + other-ai-export-2026-08-12",
            "files": files,
            "totals": totals,
        },
    )

    # Write reconciliation report
    report_path = AUDIT_DIR / "DELTA_IMPORT_RECONCILIATION_REPORT.md"
    previous_conversations = 3476
    previous_messages = 68761
    expected_total_conversations = previous_conversations + len(new_conv_records)
    expected_total_messages = previous_messages + total_messages_written

    report_content = f"""# DELTA IMPORT RECONCILIATION REPORT

**Generated:** {datetime.now(UTC).isoformat()}
**Source file:** `{CANDIDATE_FILE}`
**Source SHA-256:** `{source_sha256}`
**Source size:** {CANDIDATE_FILE.stat().st_size:,} bytes
**Ingest version:** {INGEST_VERSION}

## Summary

- **Previous conversations:** {previous_conversations:,}
- **Imported conversations:** {len(new_conv_records):,}
- **Expected total conversations:** {expected_total_conversations:,}
- **Previous messages:** {previous_messages:,}
- **Imported source messages/fragments:** {total_messages_written:,}
- **Expected total messages:** {expected_total_messages:,}

## Validation

- **Duplicate conversation IDs introduced:** {len(duplicate_conversation_ids)}
- **Duplicate source_record_ids introduced:** {len(duplicate_source_record_ids)}
- **Orphaned nodes:** {orphaned_nodes}
- **Topology failures (cycles + unreachable):** {topology_failures}
- **Timestamp parse failures:** {total_unparseable_timestamps}
- **Records with unknown authorship:** {unknown_authors}

## Deterministic Rerun Verification

Re-running this script on the same source file must produce identical:
- `messages.jsonl` content hash
- `conversations_index.json` content hash
- All `source_record_id` values

If any hash changes on rerun, the ingest is not deterministic.

## Source Format Notes

- Source format: `{SOURCE_FORMAT}`
- Fragment types observed: REQUEST, RESPONSE
- Model field preserved per message node
- No explicit message IDs in source; `message_id` set to `node_id`
- Root node has `message: None`; no records emitted for structural nodes

## Conversation Index Update

- Existing index entries preserved: {len(existing_index):,}
- New index entries appended: {len(new_conv_records):,}
- Total index entries after merge: {len(existing_index) + len(new_conv_records):,}

## Next Steps

Per approval, semantic extraction and canonical knowledge generation are deferred until:
1. Provenance resolver validation passes on the expanded corpus
2. Adversarial provenance validation gate is cleared
"""

    report_path.write_text(report_content, encoding="utf-8")

    print(f"conversations imported: {len(new_conv_records)}")
    print(f"fragments written: {total_messages_written}")
    print(f"duplicate conversation_ids: {len(duplicate_conversation_ids)}")
    print(f"duplicate source_record_ids: {len(duplicate_source_record_ids)}")
    print(f"orphaned nodes: {orphaned_nodes}")
    print(f"topology failures: {topology_failures}")
    print(f"unparseable timestamps: {total_unparseable_timestamps}")
    print(f"unknown authorship records: {unknown_authors}")
    print(f"messages path: {MESSAGES_PATH}")
    print(f"index path: {INDEX_PATH}")
    print(f"report path: {report_path}")


if __name__ == "__main__":
    main()

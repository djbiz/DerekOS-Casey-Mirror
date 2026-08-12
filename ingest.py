#!/usr/bin/env python3
"""
DerekOS Master Brain — Phase 1 Ingestion Pipeline

Parses raw ChatGPT conversation exports and produces normalized records
in 01_INGEST/conversations/*.json.

Usage:
    python ingest.py [--source-dir PATH] [--output-dir PATH] [--limit N]

Output:
    01_INGEST/
    ├── manifest.json          # Ingestion status per source file
    ├── conversations/
    │   ├── 000.json           # Normalized conversations from conversations-000.json
    │   ├── ...
    │   └── 034.json
    └── stats.json             # Aggregate statistics
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "00_RAW_ARCHIVE"
OUTPUT_DIR = ROOT / "01_INGEST"
CONVERSATIONS_DIR = OUTPUT_DIR / "conversations"

# Source file pattern
SOURCE_PATTERN = "conversations-{index:03d}.json"


def ensure_dirs():
    """Create output directories."""
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Message parsing
# ---------------------------------------------------------------------------

def parse_timestamp(ts: float | None) -> str | None:
    """Convert Unix timestamp to ISO 8601 string."""
    if ts is None:
        return None
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.isoformat()
    except (OSError, ValueError, OverflowError):
        return None


def extract_text_from_parts(parts: list[Any]) -> str:
    """Extract text content from message parts array.

    Parts can be:
    - Simple strings
    - Dicts with 'type' and content fields
    - Multi-modal content (text + images)
    """
    if not parts:
        return ""

    text_parts = []
    for part in parts:
        if isinstance(part, str):
            text_parts.append(part)
        elif isinstance(part, dict):
            # Handle different content types
            if part.get("type") == "text":
                text_parts.append(part.get("text", ""))
            elif part.get("type") == "image_url":
                text_parts.append("[image]")
            elif part.get("type") == "image_file":
                text_parts.append(f"[image_file:{part.get('file_path', 'unknown')}]")
            else:
                # Unknown part type — extract any text field
                for key in ("text", "content", "value"):
                    if key in part and isinstance(part[key], str):
                        text_parts.append(part[key])
                        break
        else:
            text_parts.append(str(part))

    return "\n".join(text_parts)


def walk_message_chain(mapping: dict, current_node_id: str | None) -> list[dict]:
    """Walk the message chain from leaf to root, returning messages in reverse order.

    ChatGPT exports use a linked-list structure where each node has a 'parent'.
    We walk from current_node (leaf) up to the root, then reverse for chronological order.
    """
    messages = []
    visited = set()
    node_id = current_node_id

    while node_id and node_id not in visited:
        visited.add(node_id)
        node = mapping.get(node_id)
        if not node:
            break

        msg = node.get("message")
        if msg:
            messages.append(msg)

        node_id = node.get("parent")

    # Reverse to get chronological order (root → leaf)
    messages.reverse()
    return messages


def normalize_message(msg: dict) -> dict:
    """Normalize a single message into the standard schema."""
    author = msg.get("author", {})
    content = msg.get("content", {})
    metadata = msg.get("metadata", {})

    # Extract text content
    parts = content.get("parts", [])
    content_text = extract_text_from_parts(parts)
    content_type = content.get("content_type", "text")

    # Determine if multimodal
    has_images = any(
        isinstance(p, dict) and p.get("type") in ("image_url", "image_file")
        for p in parts
    )
    if has_images and content_type == "text":
        content_type = "multimodal_text"

    # Build normalized message
    create_time = msg.get("create_time")
    return {
        "id": msg.get("id", ""),
        "parent_id": msg.get("metadata", {}).get("parent_id"),
        "author_role": author.get("role", "unknown"),
        "author_name": author.get("name"),
        "content_type": content_type,
        "content_text": content_text,
        "content_preview": content_text[:300] if content_text else "",
        "content_length": len(content_text),
        "create_time": create_time,
        "create_time_iso": parse_timestamp(create_time),
        "model_slug": metadata.get("model_slug"),
        "has_attachments": False,  # Will be set later if needed
        "metadata": {
            k: v for k, v in metadata.items()
            if k not in ("model_slug", "parent_id")
        },
    }


# ---------------------------------------------------------------------------
# Conversation parsing
# ---------------------------------------------------------------------------

def parse_conversation(conv: dict, source_file: str, source_index: int) -> dict:
    """Parse a single conversation into normalized format."""
    mapping = conv.get("mapping", {})
    current_node = conv.get("current_node")

    # Walk the message chain
    raw_messages = walk_message_chain(mapping, current_node)

    # Normalize messages
    messages = [normalize_message(m) for m in raw_messages]

    # Compute date range
    timestamps = [m["create_time"] for m in messages if m["create_time"]]
    date_range = None
    if timestamps:
        first_ts = min(timestamps)
        last_ts = max(timestamps)
        duration = (last_ts - first_ts) / 60.0 if last_ts > first_ts else 0
        date_range = {
            "first_message": parse_timestamp(first_ts),
            "last_message": parse_timestamp(last_ts),
            "duration_minutes": round(duration, 1),
        }

    # Count by role
    user_count = sum(1 for m in messages if m["author_role"] == "user")
    assistant_count = sum(1 for m in messages if m["author_role"] == "assistant")

    # Check for attachments
    has_attachments = any(m.get("has_attachments") for m in messages)

    # Get model from first assistant message or conversation default
    model = conv.get("default_model_slug")
    if not model:
        for m in messages:
            if m["author_role"] == "assistant" and m.get("model_slug"):
                model = m["model_slug"]
                break

    # Build normalized conversation
    create_time = conv.get("create_time")
    update_time = conv.get("update_time")

    return {
        "id": conv.get("id", ""),
        "source_file": source_file,
        "source_index": source_index,
        "title": conv.get("title", ""),
        "create_time": parse_timestamp(create_time),
        "update_time": parse_timestamp(update_time),
        "model": model,
        "is_archived": conv.get("is_archived", False),
        "is_starred": conv.get("is_starred", False),
        "message_count": len(messages),
        "user_message_count": user_count,
        "assistant_message_count": assistant_count,
        "date_range": date_range,
        "messages": messages,
        "has_attachments": has_attachments,
        "plugin_ids": conv.get("plugin_ids", []),
    }


# ---------------------------------------------------------------------------
# Source index building
# ---------------------------------------------------------------------------

def build_source_indexes(
    all_conversations: list[dict],
    output_dir: Path,
) -> dict:
    """Build source index structures for 13_SOURCE_INDEX/."""
    index_dir = output_dir.parent / "13_SOURCE_INDEX"
    by_conversation_dir = index_dir / "by_conversation"
    by_date_dir = index_dir / "by_date"
    by_evidence_dir = index_dir / "by_evidence_class"

    for d in [by_conversation_dir, by_date_dir, by_evidence_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # By conversation — map each conversation to its thought/message summary
    conv_index = {}
    for conv in all_conversations:
        conv_index[conv["id"]] = {
            "title": conv["title"],
            "source_file": conv["source_file"],
            "date": conv["create_time"][:10] if conv["create_time"] else None,
            "message_count": conv["message_count"],
            "user_message_count": conv["user_message_count"],
            "has_attachments": conv["has_attachments"],
        }

    (by_conversation_dir / "index.json").write_text(
        json.dumps(conv_index, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # By date — group conversations by year-month
    by_month = {}
    for conv in all_conversations:
        if conv["create_time"]:
            month = conv["create_time"][:7]  # YYYY-MM
            if month not in by_month:
                by_month[month] = []
            by_month[month].append({
                "id": conv["id"],
                "title": conv["title"],
                "source_file": conv["source_file"],
                "message_count": conv["message_count"],
            })

    for month, convs in sorted(by_month.items()):
        (by_date_dir / f"{month}.json").write_text(
            json.dumps(convs, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # By evidence class — placeholder (will be populated by Phase 2)
    (by_evidence_dir / "index.json").write_text(
        json.dumps({
            "_note": "Evidence class index will be populated by Phase 2 extraction",
            "_status": "pending",
        }, indent=2),
        encoding="utf-8",
    )

    # Manifest
    (index_dir / "manifest.json").write_text(
        json.dumps({
            "by_conversation": len(conv_index),
            "by_date_months": len(by_month),
            "by_evidence_class": "pending_phase2",
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }, indent=2),
        encoding="utf-8",
    )

    return conv_index


# ---------------------------------------------------------------------------
# Main ingestion
# ---------------------------------------------------------------------------

def ingest_all(source_dir: Path, output_dir: Path, limit: int | None = None) -> dict:
    """Ingest all conversation files and produce normalized output."""
    ensure_dirs()

    manifest = {
        "version": "1.0.0",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "source_dir": str(source_dir),
        "files": {},
        "total_conversations": 0,
        "total_messages": 0,
    }

    all_conversations = []
    file_count = 0

    for i in range(35):  # conversations-000 through conversations-034
        source_file = SOURCE_PATTERN.format(index=i)
        source_path = source_dir / source_file

        if not source_path.exists():
            manifest["files"][source_file] = {
                "status": "missing",
                "error": f"File not found: {source_path}",
            }
            continue

        print(f"  Parsing {source_file}...", end=" ", flush=True)
        t0 = time.time()

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                raw_convs = json.load(f)

            conversations = []
            for j, conv in enumerate(raw_convs):
                parsed = parse_conversation(conv, source_file, j)
                conversations.append(parsed)
                all_conversations.append(parsed)

            # Write output
            output_file = f"{i:03d}.json"
            output_path = CONVERSATIONS_DIR / output_file
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(conversations, f, indent=2, ensure_ascii=False)

            duration = time.time() - t0
            msg_count = sum(c["message_count"] for c in conversations)

            manifest["files"][source_file] = {
                "status": "ok",
                "output_file": output_file,
                "conversation_count": len(conversations),
                "message_count": msg_count,
                "duration_s": round(duration, 2),
            }

            manifest["total_conversations"] += len(conversations)
            manifest["total_messages"] += msg_count

            print(f"OK ({len(conversations)} convs, {msg_count} msgs, {duration:.1f}s)")

        except Exception as e:
            manifest["files"][source_file] = {
                "status": "error",
                "error": str(e),
            }
            print(f"ERROR: {e}")

        file_count += 1
        if limit and file_count >= limit:
            print(f"  --limit {limit} reached, stopping.")
            break

    # Build source indexes
    print("\n  Building source indexes...", end=" ", flush=True)
    build_source_indexes(all_conversations, output_dir)
    print("OK")

    # Generate stats
    stats = generate_stats(all_conversations, manifest)

    # Write manifest
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Write stats
    (output_dir / "stats.json").write_text(
        json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return manifest


def generate_stats(conversations: list[dict], manifest: dict) -> dict:
    """Generate aggregate statistics."""
    dates = []
    models = {}
    total_user_msgs = 0
    total_assistant_msgs = 0
    total_chars = 0
    long_conversations = []
    short_conversations = []

    for conv in conversations:
        # Date range
        if conv["create_time"]:
            dates.append(conv["create_time"])

        # Model usage
        model = conv.get("model", "unknown")
        if model:
            models[model] = models.get(model, 0) + 1

        # Message counts
        total_user_msgs += conv.get("user_message_count", 0)
        total_assistant_msgs += conv.get("assistant_message_count", 0)

        # Character counts
        for msg in conv.get("messages", []):
            total_chars += msg.get("content_length", 0)

        # Conversation length distribution
        mc = conv.get("message_count", 0)
        if mc >= 20:
            long_conversations.append({
                "id": conv["id"],
                "title": conv["title"],
                "message_count": mc,
            })
        elif mc <= 2:
            short_conversations.append({
                "id": conv["id"],
                "title": conv["title"],
                "message_count": mc,
            })

    dates.sort()

    return {
        "total_conversations": len(conversations),
        "total_messages": total_user_msgs + total_assistant_msgs,
        "total_user_messages": total_user_msgs,
        "total_assistant_messages": total_assistant_msgs,
        "total_characters": total_chars,
        "date_range": {
            "earliest": dates[0] if dates else None,
            "latest": dates[-1] if dates else None,
            "span_days": (
                (datetime.fromisoformat(dates[-1]) - datetime.fromisoformat(dates[0])).days
                if len(dates) >= 2
                else 0
            ),
        },
        "model_usage": models,
        "conversations_by_length": {
            "long_20plus_messages": len(long_conversations),
            "short_1to2_messages": len(short_conversations),
        },
        "sample_long_conversations": sorted(
            long_conversations, key=lambda x: x["message_count"], reverse=True
        )[:10],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="DerekOS Master Brain Ingestion Pipeline")
    parser.add_argument("--source-dir", type=Path, default=SOURCE_DIR,
                        help="Directory containing raw conversation JSONs")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory for normalized records")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit to first N source files (for testing)")

    args = parser.parse_args()

    print("=" * 60)
    print("  DerekOS Master Brain — Phase 1 Ingestion")
    print("=" * 60)
    print()
    print(f"  Source: {args.source_dir}")
    print(f"  Output: {args.output_dir}")
    print()

    manifest = ingest_all(args.source_dir, args.output_dir, args.limit)

    print()
    print("=" * 60)
    print(f"  CONVERSATIONS: {manifest['total_conversations']}")
    print(f"  MESSAGES:      {manifest['total_messages']}")
    print(f"  FILES:         {len(manifest['files'])}")
    print("=" * 60)

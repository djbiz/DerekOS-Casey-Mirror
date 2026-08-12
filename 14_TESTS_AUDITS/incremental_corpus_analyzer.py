"""
INCREMENTAL_CORPUS_IMPORT_ANALYZER

Analyzes a candidate ChatGPT export against the canonical DerekOS Master Brain
corpus without modifying anything. Produces INCREMENTAL_CORPUS_IMPORT_REPORT.

Usage:
    python incremental_corpus_analyzer.py <path_to_candidate_json>

Output:
    D:\Projects\VOX\DerekOS_Master_Brain\14_TESTS_AUDITS\INCREMENTAL_CORPUS_IMPORT_REPORT.md
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INGEST = ROOT / "01_INGEST"
AUDITS = Path(__file__).resolve().parent
RAW_ARCHIVE = ROOT / "00_RAW_ARCHIVE" / "chatgpt"

# ── Helpers ─────────────────────────────────────────────────────────────


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path):
    with path.open(encoding="utf-8") as f:
        return json.load(f)


# ── Extract conversation/message IDs from candidate ──────────────────────

def extract_candidate_ids(candidate_path: Path) -> dict:
    """Extract conversation IDs and message IDs from candidate export."""
    data = load_json(candidate_path)
    conversations = []
    message_ids = set()
    conv_message_counts = {}
    synthetic_msg_map = {}  # node_id -> synthetic message id

    for conv in data:
        conv_id = conv.get("id")
        if not conv_id:
            continue
        conversations.append(conv_id)
        msg_count = 0
        mapping = conv.get("mapping", {})
        for node_id, node in mapping.items():
            msg = node.get("message")
            if msg:
                # Synthetic message ID: conv_id + node_id
                synthetic_id = f"{conv_id}:{node_id}"
                message_ids.add(synthetic_id)
                synthetic_msg_map[synthetic_id] = {
                    "conversation_id": conv_id,
                    "node_id": node_id,
                    "parent": node.get("parent"),
                    "children": node.get("children", []),
                    "fragments": msg.get("fragments", []),
                }
                msg_count += 1
        conv_message_counts[conv_id] = msg_count

    return {
        "conversation_ids": set(conversations),
        "message_ids": message_ids,
        "conv_message_counts": conv_message_counts,
        "total_conversations": len(conversations),
        "total_messages": len(message_ids),
        "raw_data": data,
        "synthetic_msg_map": synthetic_msg_map,
    }


# ── Load existing canonical IDs ─────────────────────────────────────────

def load_canonical_ids() -> dict:
    """Load existing conversation and message IDs from canonical corpus."""
    canonical_conv_ids = set()
    canonical_message_ids = set()
    canonical_conv_metadata = {}

    # Load from raw archive
    for f in RAW_ARCHIVE.glob("conversations-*.json"):
        try:
            data = load_json(f)
            for conv in data:
                conv_id = conv.get("id")
                if conv_id:
                    canonical_conv_ids.add(conv_id)
                    msg_count = 0
                    for node in conv.get("mapping", {}).values():
                        msg = node.get("message")
                        if msg and msg.get("id"):
                            canonical_message_ids.add(msg["id"])
                            msg_count += 1
                    canonical_conv_metadata[conv_id] = {
                        "source_file": f.name,
                        "message_count": msg_count,
                        "title": conv.get("title", ""),
                    }
        except Exception as e:
            print(f"Warning: could not parse {f}: {e}", file=sys.stderr)

    # Also load from 01_INGEST/messages.jsonl for message-level verification
    ingested_message_ids = set()
    if (INGEST / "messages.jsonl").exists():
        with (INGEST / "messages.jsonl").open(encoding="utf-8") as f:
            for line in f:
                try:
                    m = json.loads(line)
                    ingested_message_ids.add(m.get("message_id"))
                except json.JSONDecodeError:
                    continue

    return {
        "conversation_ids": canonical_conv_ids,
        "message_ids": canonical_message_ids,
        "ingested_message_ids": ingested_message_ids,
        "conv_metadata": canonical_conv_metadata,
    }


# ── Comparison logic ────────────────────────────────────────────────────

def compare_corpora(candidate: dict, canonical: dict) -> dict:
    """Compare candidate against canonical corpus."""
    cand_conv_ids = candidate["conversation_ids"]
    cand_msg_ids = candidate["message_ids"]
    canon_conv_ids = canonical["conversation_ids"]
    canon_msg_ids = canonical["message_ids"]

    new_conv_ids = cand_conv_ids - canon_conv_ids
    overlapping_conv_ids = cand_conv_ids & canon_conv_ids

    # For overlapping conversations, check if they're exact duplicates or have new content
    overlapping_new_messages = {}
    overlapping_extra_messages = {}
    conflicting_versions = []

    for conv_id in overlapping_conv_ids:
        # Get candidate conversation
        cand_conv = next(
            (c for c in candidate["raw_data"] if c.get("id") == conv_id), None
        )
        if not cand_conv:
            continue

        cand_msgs = set()
        for node in cand_conv.get("mapping", {}).values():
            msg = node.get("message")
            if msg and msg.get("id"):
                cand_msgs.add(msg["id"])

        # Check canonical
        canon_file = canonical["conv_metadata"].get(conv_id, {}).get("source_file")
        if canon_file:
            canon_path = RAW_ARCHIVE / canon_file
            try:
                canon_data = load_json(canon_path)
                canon_conv = next(
                    (c for c in canon_data if c.get("id") == conv_id), None
                )
                if canon_conv:
                    canon_msgs = set()
                    for node in canon_conv.get("mapping", {}).values():
                        msg = node.get("message")
                        if msg and msg.get("id"):
                            canon_msgs.add(msg["id"])

                    new_in_candidate = cand_msgs - canon_msgs
                    missing_in_candidate = canon_msgs - cand_msgs

                    if not new_in_candidate and not missing_in_candidate:
                        overlapping_new_messages[conv_id] = {
                            "status": "exact_duplicate",
                            "candidate_messages": len(cand_msgs),
                            "canonical_messages": len(canon_msgs),
                        }
                    elif new_in_candidate:
                        overlapping_extra_messages[conv_id] = {
                            "status": "candidate_has_new_messages",
                            "new_message_count": len(new_in_candidate),
                            "new_message_ids": list(new_in_candidate)[:10],
                            "missing_count": len(missing_in_candidate),
                        }
                    else:
                        conflicting_versions.append({
                            "conversation_id": conv_id,
                            "status": "candidate_missing_messages",
                            "missing_count": len(missing_in_candidate),
                        })
            except Exception as e:
                conflicting_versions.append({
                    "conversation_id": conv_id,
                    "status": "error_checking_canonical",
                    "error": str(e),
                })

    return {
        "new_conversations": new_conv_ids,
        "overlapping_conversations": overlapping_conv_ids,
        "exact_duplicates": {
            conv_id: info
            for conv_id, info in overlapping_new_messages.items()
            if info["status"] == "exact_duplicate"
        },
        "overlapping_with_new_content": overlapping_extra_messages,
        "conflicting_versions": conflicting_versions,
    }


# ── Report generation ───────────────────────────────────────────────────

def generate_report(
    candidate_path: Path,
    candidate: dict,
    canonical: dict,
    comparison: dict,
    source_hash: str,
) -> str:
    """Generate markdown import report."""
    new_conv_count = len(comparison["new_conversations"])
    overlap_conv_count = len(comparison["overlapping_conversations"])
    exact_dup_count = len(comparison["exact_duplicates"])
    new_content_count = len(comparison["overlapping_with_new_content"])
    conflict_count = len(comparison["conflicting_versions"])

    lines = [
        "# INCREMENTAL CORPUS IMPORT REPORT",
        "",
        f"**Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"**Candidate file:** `{candidate_path.name}`",
        f"**Source SHA-256:** `{source_hash}`",
        f"**Source size:** {candidate_path.stat().st_size:,} bytes ({candidate_path.stat().st_size / 1024 / 1024:.1f} MB)",
        "",
        "## Summary",
        "",
        f"- **Candidate conversations:** {candidate['total_conversations']:,}",
        f"- **Candidate messages:** {candidate['total_messages']:,}",
        f"- **Canonical conversations:** {len(canonical['conversation_ids']):,}",
        f"- **Canonical messages (raw archive):** {len(canonical['message_ids']):,}",
        f"- **Canonical messages (ingested):** {len(canonical['ingested_message_ids']):,}",
        "",
        "## Comparison Results",
        "",
        f"- **New conversations:** {new_conv_count:,}",
        f"- **Overlapping conversations:** {overlap_conv_count:,}",
        f"  - Exact duplicates: {exact_dup_count:,}",
        f"  - With new/additional content: {new_content_count:,}",
        f"  - Conflicting versions: {conflict_count:,}",
        "",
        "## New Conversations (sample)",
        "",
    ]

    if comparison["new_conversations"]:
        sample_new = list(comparison["new_conversations"])[:20]
        for conv_id in sample_new:
            conv = next((c for c in candidate["raw_data"] if c.get("id") == conv_id), None)
            title = conv.get("title", "(untitled)") if conv else "(unknown)"
            lines.append(f"- `{conv_id}` — {title}")
        if new_conv_count > 20:
            lines.append(f"- ... and {new_conv_count - 20:,} more")
    else:
        lines.append("_No new conversations found._")

    lines.extend([
        "",
        "## Overlapping Conversations (sample)",
        "",
    ])

    if comparison["overlapping_conversations"]:
        sample_overlap = list(comparison["overlapping_conversations"])[:20]
        for conv_id in sample_overlap:
            canon_meta = canonical["conv_metadata"].get(conv_id, {})
            canon_title = canon_meta.get("title", "(unknown)")
            canon_file = canon_meta.get("source_file", "unknown")
            overlap_info = comparison["overlapping_with_new_content"].get(conv_id, {})
            status = overlap_info.get("status", "exact_duplicate")
            lines.append(f"- `{conv_id}` — status: {status} — canonical: `{canon_file}` ({canon_title})")
        if overlap_conv_count > 20:
            lines.append(f"- ... and {overlap_conv_count - 20:,} more")
    else:
        lines.append("_No overlapping conversations found._")

    lines.extend([
        "",
        "## Recommendation",
        "",
    ])

    if new_conv_count > 0:
        lines.append(
            f"**APPROVE INCREMENTAL IMPORT.** {new_conv_count:,} new conversations "
            f"detected. Proceed with delta ingestion into `01_INGEST/` while "
            f"preserving source provenance (source_file, conversation_id, "
            f"message_id, timestamps, parent/child topology, source_hash)."
        )
    else:
        lines.append(
            "**NO ACTION REQUIRED.** Candidate contains no new conversations. "
            "File may be a duplicate export or subset of existing corpus."
        )

    if exact_dup_count > 0:
        lines.append(
            f"\n**Note:** {exact_dup_count:,} conversations are exact duplicates of "
            f"canonical content. Skip these during import."
        )

    if comparison["conflicting_versions"]:
        lines.append(
            f"\n**Warning:** {conflict_count:,} conflicting versions detected. "
            f"Review manually before import."
        )

    lines.extend([
        "",
        "---",
        "",
        "_This report was generated automatically. Do not modify the frozen Gold Set._",
    ])

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("Usage: python incremental_corpus_analyzer.py <path_to_candidate_json>")
        sys.exit(1)

    candidate_path = Path(sys.argv[1])
    if not candidate_path.exists():
        print(f"Error: candidate file not found: {candidate_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing: {candidate_path}")
    print(f"File size: {candidate_path.stat().st_size:,} bytes")

    # Hash source file
    source_hash = sha256_file(candidate_path)
    print(f"SHA-256: {source_hash}")

    # Extract candidate IDs
    print("Extracting candidate conversation/message IDs...")
    candidate = extract_candidate_ids(candidate_path)
    print(f"  Conversations: {candidate['total_conversations']:,}")
    print(f"  Messages: {candidate['total_messages']:,}")

    # Load canonical IDs
    print("Loading canonical corpus IDs...")
    canonical = load_canonical_ids()
    print(f"  Canonical conversations: {len(canonical['conversation_ids']):,}")
    print(f"  Canonical messages (raw): {len(canonical['message_ids']):,}")
    print(f"  Canonical messages (ingested): {len(canonical['ingested_message_ids']):,}")

    # Compare
    print("Comparing corpora...")
    comparison = compare_corpora(candidate, canonical)
    print(f"  New conversations: {len(comparison['new_conversations']):,}")
    print(f"  Overlapping: {len(comparison['overlapping_conversations']):,}")
    print(f"  Exact duplicates: {len(comparison['exact_duplicates']):,}")
    print(f"  With new content: {len(comparison['overlapping_with_new_content']):,}")
    print(f"  Conflicts: {len(comparison['conflicting_versions']):,}")

    # Generate report
    report = generate_report(candidate_path, candidate, canonical, comparison, source_hash)
    report_path = AUDITS / "INCREMENTAL_CORPUS_IMPORT_REPORT.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\nWrote: {report_path}")


if __name__ == "__main__":
    main()

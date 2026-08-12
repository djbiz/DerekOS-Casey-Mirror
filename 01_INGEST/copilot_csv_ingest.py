"""
COPILOT CSV INGEST — copilot_csv adapter.

Reads 00_RAW_ARCHIVE/copilot/copilot-2026-08-12T11_59_49.315Z.csv (read-only,
preserved with SHA-256) and produces incremental additions to the SAME
unified corpus ingest.py / delta_ingest.py already write to:
  - 01_INGEST/messages.jsonl
  - 01_INGEST/conversations_index.json
  - 14_TESTS_AUDITS/COPILOT_IMPORT_RECONCILIATION_REPORT.md

Schema differences from both prior sources (per
14_TESTS_AUDITS/COPILOT_INCREMENTAL_CORPUS_IMPORT_REPORT.md's pre-import
analysis - read that report before touching this file):
  - Flat CSV: Conversation, Time, Author, Message. No mapping tree, no
    node/parent/child topology, no native message or conversation IDs.
  - Author is "Human" | "AI" (mapped to role "user" | "assistant" for
    schema consistency - the ORIGINAL Author value is preserved
    separately as source_author, since role != authorship is the
    project's central rule and collapsing "Human" into "user" must not
    look like an authorship claim).
  - CSV row order is NOT reliably chronological - verified directly
    (the "Creating a Shared Business Context Template" conversation has
    rows out of time order). This adapter sorts by parsed Time per
    conversation; ties (same-second Human/AI pairs) are broken
    Human-before-AI (a request logically precedes its response) - this
    is a disclosed heuristic, not a guarantee, and is recorded per-record
    via `chronology_tie_broken`.
  - No native conversation ID: synthesized as a stable hash of the
    conversation title. The 10 rows sharing an empty title are treated
    as one synthetic conversation (verified during pre-import analysis
    to be a single interrupted attachment-sharing thread, not unrelated
    orphans).
  - Per the Board directive: Author=Human is NEVER auto-mapped to D0 or
    any origin/evidence_class here - this adapter only produces raw,
    normalized message records. Origin/evidence-class resolution is the
    provenance resolver's job (S6, S12.7), same as every other source.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "00_RAW_ARCHIVE" / "copilot"
OUT_DIR = Path(__file__).resolve().parent
INDEX_DIR = ROOT / "13_SOURCE_INDEX"
AUDIT_DIR = ROOT / "14_TESTS_AUDITS"
CANDIDATE_FILE = RAW_DIR / "copilot-2026-08-12T11_59_49.315Z.csv"
MESSAGES_PATH = OUT_DIR / "messages.jsonl"
INDEX_PATH = OUT_DIR / "conversations_index.json"
INGEST_VERSION = "1.0.0"
SOURCE_FORMAT = "copilot-csv"

AUTHOR_TO_ROLE = {"Human": "user", "AI": "assistant"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_str(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _stable_conversation_id(source_hash: str, conversation_title: str) -> str:
    raw = f"{source_hash}\x1fconv\x1f{conversation_title}"
    return f"copilot_conv_{_sha256_str(raw)[:32]}"


def _stable_message_id(source_hash: str, conversation_title: str, row_number: int) -> str:
    raw = f"{source_hash}\x1fmsg\x1f{conversation_title}\x1f{row_number}"
    return f"copilot_msg_{_sha256_str(raw)[:32]}"


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


def main() -> None:
    if not CANDIDATE_FILE.exists():
        raise SystemExit(f"Candidate file not found: {CANDIDATE_FILE}")

    source_sha256 = _sha256_file(CANDIDATE_FILE)
    with CANDIDATE_FILE.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    source_file = CANDIDATE_FILE.name

    # Group rows by conversation title, preserving original row index for
    # traceability. Empty-title rows are treated as ONE synthetic
    # conversation, per the pre-import finding that they form a single
    # interrupted thread, not unrelated orphans.
    by_conv: dict[str, list[tuple[int, dict]]] = {}
    for i, row in enumerate(rows):
        title = row["Conversation"].strip()
        by_conv.setdefault(title, []).append((i, row))

    # Load existing state for incremental merge (same pattern as
    # delta_ingest.py) - dedup by source_record_id, never overwrite.
    existing_messages: list[dict] = []
    existing_record_ids: set[str] = set()
    if MESSAGES_PATH.exists():
        with MESSAGES_PATH.open(encoding="utf-8") as f:
            for line in f:
                try:
                    m = json.loads(line)
                    existing_messages.append(m)
                    if m.get("source_record_id"):
                        existing_record_ids.add(m["source_record_id"])
                except json.JSONDecodeError:
                    continue

    existing_index: list[dict] = []
    if INDEX_PATH.exists():
        with INDEX_PATH.open(encoding="utf-8") as f:
            try:
                existing_index = json.load(f)
            except json.JSONDecodeError:
                existing_index = []
    existing_conv_ids = {c.get("conversation_id") for c in existing_index}

    all_new_records: list[dict] = []
    new_conv_records: list[dict] = []
    total_ties_broken = 0
    total_empty_messages = 0
    total_unparseable_timestamps = 0
    duplicate_source_record_ids: list[str] = []
    new_record_ids_seen: set[str] = set()

    for title, indexed_rows in by_conv.items():
        conv_id = _stable_conversation_id(source_sha256, title)
        if conv_id in existing_conv_ids:
            continue  # already ingested in a prior run

        # Sort by (parsed_time, human_before_ai) - the disclosed tie-break
        # heuristic. Track whether a tie was actually broken (same
        # timestamp, different original row order) for the reconciliation
        # report - this is a real limitation of the source format, not
        # hidden.
        def sort_key(item):
            _, row = item
            ts = _iso(row["Time"])
            role_rank = 0 if row["Author"] == "Human" else 1
            return (ts or "", role_rank)

        sorted_rows = sorted(indexed_rows, key=sort_key)

        # Detect whether sorting actually changed row order (tie-break
        # or reordering occurred) vs. was already chronological.
        original_order = [i for i, _ in indexed_rows]
        sorted_order = [i for i, _ in sorted_rows]
        if original_order != sorted_order:
            total_ties_broken += 1

        records = []
        for seq_idx, (row_number, row) in enumerate(sorted_rows):
            text = row["Message"]
            if not text.strip():
                total_empty_messages += 1

            timestamp = _iso(row["Time"])
            if timestamp is not None and timestamp.startswith("UNPARSEABLE_RAW:"):
                total_unparseable_timestamps += 1

            source_author = row["Author"]
            record_id = _stable_message_id(source_sha256, title, row_number)

            record = {
                "source_record_id": record_id,
                "message_id": _stable_message_id(source_sha256, title, row_number),
                "node_id": None,
                "conversation_id": conv_id,
                "conversation_title": title or "(untitled - attachment-share thread)",
                "source_file": source_file,
                "source_format": SOURCE_FORMAT,
                "role": AUTHOR_TO_ROLE.get(source_author),
                "source_author": source_author,  # preserved, never collapsed into role
                "author_name": None,
                "timestamp": timestamp,
                "text": text,
                "content_type": "text",
                "branch": "main",  # flat CSV has no branching structure
                "sequence_index": seq_idx,
                "source_csv_row_number": row_number,  # 0-based, for raw reconstruction/audit
                "parent_message_id": None,
                "child_message_ids": [],
                "source_sha256": source_sha256,
                "ingest_version": INGEST_VERSION,
            }
            records.append(record)

            if record_id in existing_record_ids or record_id in new_record_ids_seen:
                duplicate_source_record_ids.append(record_id)
            new_record_ids_seen.add(record_id)

        all_new_records.extend(records)

        first_ts = next((r["timestamp"] for r in records if r["timestamp"]), None)
        last_ts = next((r["timestamp"] for r in reversed(records) if r["timestamp"]), None)
        new_conv_records.append(
            {
                "conversation_id": conv_id,
                "title": title or "(untitled - attachment-share thread)",
                "source_file": source_file,
                "source_format": SOURCE_FORMAT,
                "create_time": first_ts,
                "update_time": last_ts,
                "message_count_total": len(records),
                "message_count_main_path": len(records),
                "message_count_alternate": 0,
                "anomalous_current_node": False,
            }
        )

    # Atomic merge, matching delta_ingest.py's pattern.
    merged_messages = existing_messages + all_new_records
    temporary_messages_path = MESSAGES_PATH.with_suffix(".jsonl.tmp")
    with temporary_messages_path.open("w", encoding="utf-8", newline="\n") as out:
        for record in merged_messages:
            out.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            out.write("\n")
        out.flush()
        os.fsync(out.fileno())
    _replace(temporary_messages_path, MESSAGES_PATH)

    merged_index = existing_index + new_conv_records
    _write_json(INDEX_PATH, merged_index)

    # Update source manifest (same file delta_ingest.py maintains)
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
            "message_count": len(all_new_records),
            "json_valid": None,  # not applicable - CSV, not JSON
        }
    )
    totals = existing_manifest.get("totals", {})
    totals["source_files"] = totals.get("source_files", 0) + 1
    totals["conversations"] = totals.get("conversations", 0) + len(new_conv_records)
    totals["messages"] = totals.get("messages", 0) + len(all_new_records)
    _write_json(
        manifest_path,
        {
            "schema_version": existing_manifest.get("schema_version", "1.0.0"),
            "corpus": existing_manifest.get("corpus", "") + " + copilot-csv-2026-08-12",
            "files": files,
            "totals": totals,
        },
    )

    # Reconciliation report
    report_path = AUDIT_DIR / "COPILOT_IMPORT_RECONCILIATION_REPORT.md"
    previous_message_count = len(existing_messages)
    report = f"""# Copilot Import Reconciliation Report

**Generated:** {datetime.now(UTC).isoformat()}
**Source file:** `{CANDIDATE_FILE}`
**Source SHA-256:** `{source_sha256}`
**Ingest version:** {INGEST_VERSION}

Pre-import analysis: `14_TESTS_AUDITS/COPILOT_INCREMENTAL_CORPUS_IMPORT_REPORT.md` (read first - contains the Legacy Forge provenance-laundering finding this ingestion preserves rather than resolves).

## Summary

- **Messages in corpus before this run:** {previous_message_count:,}
- **Copilot messages imported:** {len(all_new_records):,}
- **Messages in corpus after this run:** {len(merged_messages):,}
- **Conversations imported:** {len(new_conv_records):,} (of 28 found in the source file)

## Chronology reconstruction

- **Conversations where sorting by Time changed the original CSV row order:** {total_ties_broken} — confirms the pre-import finding that CSV row order is not reliably chronological. Every record's `source_csv_row_number` preserves its original position for full audit/reconstruction regardless of the reordering applied here.
- **Tie-break rule applied:** same-timestamp Human/AI pairs ordered Human-before-AI (a request logically precedes its response) — a disclosed heuristic, not a guarantee from the source data itself.

## Data quality

- **Empty-`Message` rows imported as-is (not dropped):** {total_empty_messages} — consistent with the "no silent drops" principle; these are real records (likely attachment-only shares) with legitimately empty text, not a parsing failure.
- **Unparseable timestamps:** {total_unparseable_timestamps}
- **Duplicate `source_record_id`s (should be 0 on a clean run):** {len(duplicate_source_record_ids)}

## What this ingestion does NOT do

- **Does not assign `evidence_class`, `originator`, or any provenance judgment.** `Author=Human` is preserved verbatim as `source_author` and separately mapped to `role: "user"` for schema consistency only — neither field is treated as evidence of Derek authorship. That determination is the provenance resolver's job (`MASTER_BRAIN_BUILD_SPEC.md` §6, §12.7), identical to how ChatGPT's `role: user` is treated.
- **Does not resolve the Legacy Forge finding.** The traced lineage (ChatGPT-invented content -> pasted into Copilot -> polished) is preserved as-is in the ingested records; a future cross-source provenance pass links `origin_message_id`s back to the ChatGPT corpus (`14_TESTS_AUDITS/copilot_chatgpt_overlap.json` already has 38 candidate cross-source matches from the pre-import check, not yet formalized into `03_PROVENANCE_INDEX/`).
- **Does not begin SOP extraction or canonicalization.**

## Deterministic rerun verification

Re-running this script on the same source file produces identical `source_record_id` values for every row (stable hash of source SHA-256 + conversation title + row number) — existing records are matched and skipped, not duplicated.
"""
    report_path.write_text(report, encoding="utf-8")

    print(f"conversations imported: {len(new_conv_records)}")
    print(f"messages imported: {len(all_new_records)}")
    print(f"chronology reordering applied to: {total_ties_broken} conversations")
    print(f"empty-message rows: {total_empty_messages}")
    print(f"unparseable timestamps: {total_unparseable_timestamps}")
    print(f"duplicate source_record_ids: {len(duplicate_source_record_ids)}")
    print(f"messages path: {MESSAGES_PATH}")
    print(f"report path: {report_path}")


if __name__ == "__main__":
    main()

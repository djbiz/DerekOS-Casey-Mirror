"""Independent, bounded checks for the canonical Phase 1 ingest baseline."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "00_RAW_ARCHIVE" / "chatgpt"
INGEST = ROOT / "01_INGEST"
PROFILE_SCHEMAS = {
    ("1.1.0", "chatgpt-json"): "message-1.1.0.schema.json",
    ("1.0.0", "copilot-csv"): "message-1.0.0-copilot.schema.json",
    ("2.0.0", "other-ai-export-fragments"): "message-2.0.0-fragment.schema.json",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def record_profile(record: dict) -> tuple[str, str]:
    """Return an explicit schema profile; never infer one from loose fields."""

    version = record.get("ingest_version")
    source_format = record.get("source_format", "chatgpt-json")
    profile = (version, source_format)
    if profile not in PROFILE_SCHEMAS:
        raise ValueError(f"unsupported ingest profile: {profile!r}")
    return profile


def load_schemas() -> dict[tuple[str, str], dict]:
    return {
        profile: json.loads((INGEST / "schemas" / filename).read_text(encoding="utf-8"))
        for profile, filename in PROFILE_SCHEMAS.items()
    }


def validate_versioned_record(record: dict, schemas: dict[tuple[str, str], dict]) -> tuple[str, str]:
    profile = record_profile(record)
    jsonschema.validate(record, schemas[profile])
    return profile


def main() -> None:
    schemas = load_schemas()
    report = json.loads((INGEST / "ingest_report.json").read_text(encoding="utf-8"))
    manifest = json.loads((ROOT / "13_SOURCE_INDEX" / "source_manifest.json").read_text(encoding="utf-8"))
    baseline_manifest_files = [
        item for item in manifest["files"]
        if item["filename"].startswith("conversations-") and item["filename"].endswith(".json")
    ]
    records: dict[tuple[str, str], tuple[str | None, tuple[str, ...]]] = {}
    baseline_source_record_ids: set[str] = set()
    all_source_record_ids: set[str] = set()
    profile_counts = {profile: 0 for profile in PROFILE_SCHEMAS}
    formal_samples = {profile: 0 for profile in PROFILE_SCHEMAS}
    key_mismatches = 0
    pilot_messages: dict[tuple[str, str], str] = {}
    baseline_hash = hashlib.sha256()

    with (INGEST / "messages.jsonl").open("rb") as source:
        index = 0
        while True:
            raw_line = source.readline()
            if not raw_line:
                break
            index += 1
            record = json.loads(raw_line)
            profile = record_profile(record)
            profile_counts[profile] += 1
            expected_keys = set(schemas[profile]["required"])
            if set(record) != expected_keys:
                key_mismatches += 1
            # Validate a deterministic head and interval sample for every
            # profile; strict key equality is checked for every record.
            interval = 1000 if profile == ("1.1.0", "chatgpt-json") else 100
            if profile_counts[profile] <= 100 or profile_counts[profile] % interval == 0:
                validate_versioned_record(record, schemas)
                formal_samples[profile] += 1
            all_source_record_ids.add(record["source_record_id"])
            if profile == ("1.1.0", "chatgpt-json"):
                baseline_hash.update(raw_line)
                records[(record["conversation_id"], record["node_id"])] = (
                    record["parent_message_id"],
                    tuple(record["child_message_ids"]),
                )
                baseline_source_record_ids.add(record["source_record_id"])
                pilot_messages[(record["conversation_id"], record["message_id"])] = record["source_file"]

    broken_links = 0
    for (conversation_id, node_id), (_, child_ids) in records.items():
        for child_id in child_ids:
            child = records.get((conversation_id, child_id))
            if child is None or child[0] != node_id:
                broken_links += 1

    raw_hash_mismatches = sum(
        digest(RAW / item["filename"]) != item["sha256"] for item in baseline_manifest_files
    )
    writable_raw = sum(not path.is_file() or not path.stat().st_file_attributes & 1 for path in RAW.glob("conversations-*.json"))

    pilot_failures = 0
    with (ROOT / "02_EXTRACTED_THOUGHTS" / "pilot_atomic_thoughts.jsonl").open(encoding="utf-8") as source:
        for line in source:
            thought = json.loads(line)
            message = pilot_messages.get((thought["conversation_id"], thought["message_id"]))
            if message is None or message != thought["source_file"]:
                pilot_failures += 1

    checks = {
        "source_files": len(baseline_manifest_files) == 35,
        "messages": len(records) == 68761,
        "unique_source_records": len(baseline_source_record_ids) == 68761,
        "aggregate_unique_source_records": len(all_source_record_ids) == sum(profile_counts.values()),
        "known_ingest_profiles": set(profile_counts) == set(PROFILE_SCHEMAS) and all(profile_counts.values()),
        "profile_counts": profile_counts[("1.1.0", "chatgpt-json")] == 68761,
        "node_reconciliation": report["mapping_nodes"] == report["total_messages_written"] + report["structural_nodes_without_messages"],
        "contract_keys": key_mismatches == 0,
        "formal_schema_samples": all(formal_samples.values()),
        "graph_links": broken_links == 0,
        "raw_hashes": raw_hash_mismatches == 0,
        "raw_read_only": writable_raw == 0,
        "phase2_pilot_compatibility": pilot_failures == 0,
        "report_hash": baseline_hash.hexdigest() == report["messages_sha256"],
    }
    print(json.dumps({"profile_counts": {"|".join(key): value for key, value in profile_counts.items()}}, indent=2))
    print(json.dumps(checks, indent=2, sort_keys=True))
    if not all(checks.values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

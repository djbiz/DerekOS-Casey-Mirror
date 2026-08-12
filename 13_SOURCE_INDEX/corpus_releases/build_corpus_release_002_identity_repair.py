"""
Builds CORPUS_RELEASE_002 as an explicit identity-repair child of
CORPUS_RELEASE_001 - NOT a new snapshot of the live, mutable
01_INGEST/messages.jsonl (which has been actively edited by parallel
agents since CORPUS_RELEASE_001 was frozen and now contains unrelated
changes). This script reads ONLY the immutable CORPUS_RELEASE_001 and
applies exactly one transform, so the delta between the two releases is
fully attributable to the identity fix and nothing else.

Root cause being repaired (see PROVENANCE_INDEX_V0.3_EVALUATION_REPORT.md
S1 and the Corpus Identity Integrity remediation that followed it): 42
`message_id` values are not globally unique - verified directly against
the raw sources. 39/42 are per-conversation-scoped sequential integers
native to the "other-ai-export" source's own mapping structure (correct
in that source, but never namespaced when copied into the global
message_id field at ingest time). The other 3 are ChatGPT node UUIDs
that legitimately repeat across separate conversation-branch exports
(confirmed directly in the raw conversations-023.json - e.g. three
separately-exported branches of a "Chess Business App Dev" conversation
share one early node id). Either way, `message_id` alone was never a
safe global join key.

The fix does NOT invent a new ID scheme. `source_record_id` already
exists on every CORPUS_RELEASE_001 record, is already 100% globally
unique (verified: 72,241/72,241 distinct values, zero collisions), and
is already computed deterministically from immutable source coordinates
by all three ingest paths (ingest.py, delta_ingest.py,
copilot_csv_ingest.py - each hashes source file/hash + conversation_id +
message_id, optionally + fragment_index). This script adds an explicit
`canonical_id` field (== `source_record_id`, unchanged value) so the
correct global key is self-evident to any future code reading the
corpus, rather than relying on tribal knowledge that source_record_id
(not message_id) is the safe one to use - exactly the gap that let this
bug ship in the first place. `message_id` is preserved byte-for-byte as
platform-native source metadata; nothing is destroyed or overwritten.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RELEASES_DIR = Path(__file__).resolve().parent
PARENT_RELEASE_ID = "CORPUS_RELEASE_001"
PARENT_DIR = RELEASES_DIR / PARENT_RELEASE_ID
PARENT_MESSAGES = PARENT_DIR / "messages.jsonl"
PARENT_META = RELEASES_DIR / f"{PARENT_RELEASE_ID}.json"


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    if not PARENT_MESSAGES.exists():
        raise SystemExit(f"{PARENT_MESSAGES} not found - CORPUS_RELEASE_001 must exist and stay untouched")

    parent_meta = json.loads(PARENT_META.read_text(encoding="utf-8"))
    parent_sha_recorded = parent_meta["sha256"]
    parent_sha_actual = _sha256_file(PARENT_MESSAGES)
    if parent_sha_actual != parent_sha_recorded:
        raise SystemExit(
            f"CORPUS_RELEASE_001 integrity check failed: recorded sha256 {parent_sha_recorded[:16]}... "
            f"!= actual {parent_sha_actual[:16]}... - refusing to build a child release from a "
            f"possibly-modified parent. CORPUS_RELEASE_001 must never be rewritten."
        )

    release_id = "CORPUS_RELEASE_002"
    release_dir = RELEASES_DIR / release_id
    release_dir.mkdir(exist_ok=False)

    canonical_id_seen: set[str] = set()
    message_id_conv_pairs_seen: set[tuple[str, str]] = set()
    records_written = 0
    missing_source_record_id = 0

    out_path = release_dir / "messages.jsonl"
    with PARENT_MESSAGES.open(encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            rec = json.loads(line)
            srid = rec.get("source_record_id")
            if not srid:
                missing_source_record_id += 1
                continue
            if srid in canonical_id_seen:
                raise SystemExit(f"source_record_id collision found while building {release_id}: {srid} - aborting, parent data is not what was verified")
            canonical_id_seen.add(srid)

            pair = (rec.get("message_id"), rec.get("conversation_id"))
            message_id_conv_pairs_seen.add(pair)

            # The only content change: canonical_id added, everything else
            # byte-identical to the parent record, including message_id.
            rec["canonical_id"] = srid
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")
            records_written += 1

    out_path.chmod(0o444)
    sha256 = _sha256_file(out_path)

    sources: dict[str, int] = {}
    with out_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            src = rec.get("source_format") or rec.get("source_file") or "unknown"
            sources[src] = sources.get(src, 0) + 1

    metadata = {
        "release_id": release_id,
        "records": records_written,
        "sha256": sha256,
        "sources": sources,
        "created": datetime.now(UTC).isoformat(),
        "status": "FROZEN",
        "parent": PARENT_RELEASE_ID,
        "parent_sha256": parent_sha_recorded,
        "delta": (
            "Corpus Identity Integrity remediation: added explicit `canonical_id` field "
            "(alias of the pre-existing, already-unique `source_record_id`) to every record. "
            "No other content changed - message_id preserved unmodified as platform-native "
            "source metadata. Root cause and full verification in "
            "03_PROVENANCE_INDEX/v0_3/CORPUS_IDENTITY_INTEGRITY_REPORT.md."
        ),
        "identity_repair": {
            "canonical_id_field": "canonical_id",
            "canonical_id_source": "source_record_id (pre-existing, deterministic, verified globally unique)",
            "message_id_field_preserved": True,
            "records_missing_source_record_id": missing_source_record_id,
            "distinct_canonical_ids": len(canonical_id_seen),
            "distinct_message_id_conversation_id_pairs": len(message_id_conv_pairs_seen),
        },
        "frozen_path": str(out_path),
    }
    metadata_path = RELEASES_DIR / f"{release_id}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_path.chmod(0o444)

    print(f"created {release_id}: {records_written} records, sha256={sha256[:16]}...")
    print(f"parent: {PARENT_RELEASE_ID} (sha256 verified unchanged)")
    print(f"records missing source_record_id (excluded): {missing_source_record_id}")
    print(f"distinct canonical_id values: {len(canonical_id_seen)}")
    print(json.dumps(metadata["identity_repair"], indent=2))


if __name__ == "__main__":
    main()

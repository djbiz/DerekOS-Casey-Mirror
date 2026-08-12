"""
Freezes the current 01_INGEST/messages.jsonl into an immutable,
content-addressed Corpus Release. From the moment a release is created,
every provenance job (Gold Set, adversarial benchmark, provenance index,
resolver run) must read from the frozen release directory, never from
the live, mutable 01_INGEST/messages.jsonl - which multiple agents write
to concurrently, and which has genuinely changed under running analysis
jobs multiple times this session (68,761 -> 72,241 -> 75,321 -> 72,241).

Usage: python freeze_release.py [--parent CORPUS_RELEASE_NNN] [--delta "description"]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MESSAGES_PATH = ROOT / "01_INGEST" / "messages.jsonl"
RELEASES_DIR = Path(__file__).resolve().parent


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _next_release_id() -> str:
    existing = sorted(RELEASES_DIR.glob("CORPUS_RELEASE_*.json"))
    if not existing:
        return "CORPUS_RELEASE_001"
    last_num = max(int(p.stem.split("_")[-1]) for p in existing)
    return f"CORPUS_RELEASE_{last_num + 1:03d}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parent", default=None)
    parser.add_argument("--delta", default=None)
    args = parser.parse_args()

    if not MESSAGES_PATH.exists():
        raise SystemExit(f"{MESSAGES_PATH} not found")

    release_id = _next_release_id()
    release_dir = RELEASES_DIR / release_id
    release_dir.mkdir(exist_ok=False)

    frozen_messages_path = release_dir / "messages.jsonl"
    shutil.copy2(MESSAGES_PATH, frozen_messages_path)

    # Lock it down - matching the read-only treatment already applied to
    # 00_RAW_ARCHIVE/. A frozen release is source-of-truth for provenance
    # work the same way the raw archive is for ingestion.
    frozen_messages_path.chmod(0o444)

    record_count = sum(1 for _ in frozen_messages_path.open(encoding="utf-8"))
    sha256 = _sha256_file(frozen_messages_path)

    sources: dict[str, int] = {}
    with frozen_messages_path.open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            src = rec.get("source_format") or rec.get("source_file") or "unknown"
            sources[src] = sources.get(src, 0) + 1

    metadata = {
        "release_id": release_id,
        "records": record_count,
        "sha256": sha256,
        "sources": sources,
        "created": datetime.now(UTC).isoformat(),
        "status": "FROZEN",
        "parent": args.parent,
        "delta": args.delta,
        "frozen_path": str(frozen_messages_path),
    }
    metadata_path = RELEASES_DIR / f"{release_id}.json"
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    metadata_path.chmod(0o444)

    print(f"created {release_id}: {record_count} records, sha256={sha256[:16]}...")
    print(f"frozen at: {frozen_messages_path}")
    print(f"metadata: {metadata_path}")


if __name__ == "__main__":
    main()

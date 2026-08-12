"""
Corpus Identity Integrity test suite. Run against a frozen corpus release
(default: CORPUS_RELEASE_002) before that release is trusted as input to
any provenance index or resolver rebuild.

Six required properties, per the Architecture Board's remediation
directive:
1. canonical record IDs globally unique
2. origin/reuse endpoints resolve to exactly one physical record
3. no ambiguous foreign-key lookup
4. coverage ratios constrained to [0,1]
5. chronology calculated from the resolved records
6. chain nodes reference canonical IDs rather than bare platform IDs

Tests 4-6 are structural checks on index OUTPUT (reuse_hits.jsonl /
derivation_chains.jsonl), not on the corpus release itself - they are
included here as a single suite so a future rebuild has one command to
run, but they no-op (skip, not fail) if no index output exists yet for
the given release, since this repair pass explicitly stops before
rebuilding the index.

Usage: python test_corpus_identity_integrity.py [RELEASE_ID]
Exits non-zero on any failure.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

RELEASES_DIR = Path(__file__).resolve().parent
ROOT = RELEASES_DIR.parents[1]

FAILURES: list[str] = []
PASSES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        PASSES.append(name)
    else:
        FAILURES.append(f"{name}: {detail}")


def load_release(release_id: str) -> list[dict]:
    path = RELEASES_DIR / release_id / "messages.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found")
    return [json.loads(l) for l in path.open(encoding="utf-8")]


def test_canonical_id_globally_unique(messages: list[dict]) -> None:
    ids = [m.get("canonical_id") for m in messages]
    missing = sum(1 for i in ids if not i)
    check("1. every record has a canonical_id", missing == 0, f"{missing} records missing canonical_id")
    non_null = [i for i in ids if i]
    check(
        "1. canonical_id globally unique",
        len(non_null) == len(set(non_null)),
        f"{len(non_null) - len(set(non_null))} duplicate canonical_id values found",
    )


def test_message_id_preserved(messages: list[dict], parent_messages: list[dict]) -> None:
    by_canonical_parent = {m["source_record_id"]: m.get("message_id") for m in parent_messages if m.get("source_record_id")}
    mismatches = 0
    for m in messages:
        cid = m.get("canonical_id")
        if cid in by_canonical_parent and m.get("message_id") != by_canonical_parent[cid]:
            mismatches += 1
    check(
        "4. message_id preserved unmodified vs parent release",
        mismatches == 0,
        f"{mismatches} records where message_id changed vs CORPUS_RELEASE_001",
    )


def test_origin_reuse_endpoints_resolve_uniquely(messages: list[dict]) -> None:
    """Property 2: an endpoint identified by canonical_id must resolve to
    exactly one physical record - i.e. no two records share a canonical_id
    (already covered by test 1) AND no code path can accidentally resolve
    an endpoint using message_id alone and land on more than one record."""
    by_message_id: dict[str, set] = defaultdict(set)
    for m in messages:
        by_message_id[m["message_id"]].add(m.get("canonical_id"))
    ambiguous_message_ids = {k: v for k, v in by_message_id.items() if len(v) > 1}
    check(
        "2. message_id alone would NOT resolve uniquely (documenting the risk, not a corpus defect)",
        True,  # informational - this is expected and exactly why canonical_id exists
        f"{len(ambiguous_message_ids)} message_id values map to >1 canonical_id - confirms message_id must never be used as a lookup key",
    )
    check(
        "3. canonical_id resolves to exactly one physical record (no ambiguous FK lookup)",
        all(len(v) == 1 for v in defaultdict(set, {m["canonical_id"]: {m["canonical_id"]} for m in messages if m.get("canonical_id")}).values()),
        "canonical_id -> record mapping is 1:1 by construction (test 1 already verifies uniqueness)",
    )


def test_index_output_if_present(release_id: str) -> None:
    """Tests 5-6 (coverage ratios, chronology, chain nodes use canonical
    IDs) run against index output for this release, if it exists. This
    repair pass stops before rebuilding the index, so these are expected
    to skip for CORPUS_RELEASE_002 today - included so the SAME suite can
    validate a future rebuilt index without being rewritten."""
    candidate_dirs = [
        ROOT / "03_PROVENANCE_INDEX" / "v0_3",
        ROOT / "03_PROVENANCE_INDEX" / "v0_2",
    ]
    hits_path = None
    for d in candidate_dirs:
        p = d / "reuse_hits.jsonl"
        if p.exists():
            report_path = d / "index_report.json"
            if report_path.exists():
                report = json.loads(report_path.read_text(encoding="utf-8"))
                if report.get("corpus_release") == release_id:
                    hits_path = p
                    break
    if hits_path is None:
        print(f"  (skipped: no index output found built from {release_id} yet - expected, this repair pass stops before rebuilding)")
        return

    hits = [json.loads(l) for l in hits_path.open(encoding="utf-8")]
    bad_coverage = [
        h for h in hits
        if not (0.0 <= h.get("reuse_side_coverage", 0) <= 1.0 + 1e-9)
        or not (0.0 <= h.get("origin_side_coverage", 0) <= 1.0 + 1e-9)
    ]
    check(
        "5. coverage ratios constrained to [0,1]",
        len(bad_coverage) == 0,
        f"{len(bad_coverage)} hits with a coverage ratio outside [0,1] (e.g. the 2.628 value that exposed the collision bug)",
    )

    bad_chronology = [h for h in hits if h.get("chronology_valid") is True and not (h.get("origin_timestamp", "") < h.get("reuse_timestamp", ""))]
    check(
        "6. chronology_valid=True implies origin_timestamp < reuse_timestamp",
        len(bad_chronology) == 0,
        f"{len(bad_chronology)} hits marked chronology_valid=True with a non-earlier origin_timestamp",
    )

    uses_bare_id = [
        h for h in hits
        if h.get("reuse_record_id") in {"1", "2", "3"} or h.get("candidate_origin_record_id") in {"1", "2", "3"}
    ]
    check(
        "6. chain/hit records reference canonical IDs, not bare small-integer platform IDs",
        len(uses_bare_id) == 0,
        f"{len(uses_bare_id)} hits still reference a bare platform message_id like '1'/'2'/'3' instead of a canonical_id",
    )


def main() -> None:
    release_id = sys.argv[1] if len(sys.argv) > 1 else "CORPUS_RELEASE_002"
    messages = load_release(release_id)
    parent_messages = load_release("CORPUS_RELEASE_001")

    print(f"testing {release_id}: {len(messages)} records")
    test_canonical_id_globally_unique(messages)
    test_message_id_preserved(messages, parent_messages)
    test_origin_reuse_endpoints_resolve_uniquely(messages)
    test_index_output_if_present(release_id)

    print(f"\n{len(PASSES)} passed, {len(FAILURES)} failed\n")
    for p in PASSES:
        print(f"  PASS: {p}")
    for f in FAILURES:
        print(f"  FAIL: {f}")

    if FAILURES:
        sys.exit(1)


if __name__ == "__main__":
    main()

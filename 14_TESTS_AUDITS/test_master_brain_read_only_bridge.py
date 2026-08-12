"""Acceptance tests for Slice 1 read-only canonical retrieval."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge import (
    CanonicalStoreInvalid,
    CanonicalStoreUnavailable,
    ReadOnlyCanonicalRepository,
)


RECORDS = [
    {
        "knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
        "revision": 1,
        "canonical_status": "SUPERSEDED",
        "title": "Earlier knowledge ownership rule",
        "summary": "An earlier interpretation retained for history.",
        "content": "Working documentation was once treated as canonical.",
        "evidence_ids": ["evidence-message-001"],
    },
    {
        "knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
        "revision": 2,
        "canonical_status": "CURRENT",
        "title": "Three-temperature knowledge ownership",
        "summary": "Master Brain owns canon, Obsidian is warm, and VOX is hot.",
        "content": "Historical truth belongs to Master Brain; live operations belong to VOX.",
        "evidence_ids": ["evidence-message-001", "evidence-board-002"],
    },
    {
        "knowledge_id": "MBK-VOX-ARCHITECTURE-01KTEST0002",
        "revision": 1,
        "canonical_status": "CURRENT",
        "title": "Advisory authority boundary",
        "summary": "Advisors propose work and do not authorize execution.",
        "content": "Execution authority remains external to the advisory envelope.",
        "evidence_ids": ["evidence-board-003"],
    },
]


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class ReadOnlyBridgeAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = self.root / "canonical_records.jsonl"
        self.store.write_text("".join(json.dumps(record) + "\n" for record in RECORDS), encoding="utf-8")
        self.obsidian = self.root / "obsidian"
        self.vox_state = self.root / "vox_state"
        self.wrong_docker_mount = self.root / "empty_docker_vault"
        for directory in (self.obsidian, self.vox_state, self.wrong_docker_mount):
            directory.mkdir()
        (self.obsidian / "human-note.md").write_text("human content", encoding="utf-8")
        (self.vox_state / "work-order.json").write_text('{"status":"active"}', encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def repository(self) -> ReadOnlyCanonicalRepository:
        return ReadOnlyCanonicalRepository(self.store, store_id="acceptance-fixture")

    def test_exact_knowledge_id_returns_current_revision(self) -> None:
        result = self.repository().get("MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(result["revision"], 2)
        self.assertEqual(result["canonical_status"], "CURRENT")
        self.assertEqual(result["retrieval_authority"]["retrieval_mode"], "current_revision")

    def test_exact_historical_revision_preserves_superseded_status(self) -> None:
        result = self.repository().get("MBK-DEREKOS-DECISION-01KTEST0001", revision=1)
        self.assertEqual(result["revision"], 1)
        self.assertEqual(result["canonical_status"], "SUPERSEDED")
        self.assertEqual(result["retrieval_authority"]["retrieval_mode"], "exact_revision")

    def test_query_search_defaults_to_current_canonical_records(self) -> None:
        results = self.repository().search("knowledge canonical VOX")
        self.assertTrue(results)
        self.assertTrue(all(item["canonical_status"] == "CURRENT" for item in results))
        self.assertEqual(results[0]["knowledge_id"], "MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(results[0]["retrieval_authority"]["retrieval_mode"], "direct_canonical_text")

    def test_query_can_explicitly_include_history(self) -> None:
        results = self.repository().search("working documentation canonical", include_history=True)
        self.assertTrue(any(item["canonical_status"] == "SUPERSEDED" for item in results))

    def test_evidence_links_and_authority_metadata_are_preserved(self) -> None:
        result = self.repository().get("MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(result["provenance"]["evidence_ids"], RECORDS[1]["evidence_ids"])
        self.assertEqual(result["source_authority"], "MASTER_BRAIN_CANONICAL_STORE")
        self.assertEqual(result["authority_class"], "AUTHORITATIVE")
        self.assertEqual(result["source_temperature"], "COLD_DEEP")
        self.assertIsNone(result["retrieval_authority"]["indexed_from"])
        self.assertEqual(result["retrieval_authority"]["store_id"], "acceptance-fixture")
        self.assertEqual(len(result["retrieval_authority"]["store_sha256"]), 64)

    def test_retrieval_does_not_write_obsidian_vox_or_store(self) -> None:
        before = tree_digest(self.root)
        repository = self.repository()
        repository.get("MBK-DEREKOS-DECISION-01KTEST0001")
        repository.search("authority execution")
        after = tree_digest(self.root)
        self.assertEqual(before, after)

    def test_missing_canonical_store_fails_without_fallback(self) -> None:
        with self.assertRaisesRegex(CanonicalStoreUnavailable, "canonical store unavailable"):
            ReadOnlyCanonicalRepository(self.root / "missing.jsonl")

    def test_empty_canonical_store_fails_without_fallback(self) -> None:
        empty = self.root / "empty.jsonl"
        empty.write_bytes(b"")
        with self.assertRaisesRegex(CanonicalStoreUnavailable, "canonical store is empty"):
            ReadOnlyCanonicalRepository(empty)

    def test_duplicate_current_revision_state_fails_closed(self) -> None:
        bad_store = self.root / "ambiguous.jsonl"
        duplicate_current = dict(RECORDS[0], canonical_status="CURRENT")
        bad_store.write_text(
            json.dumps(duplicate_current) + "\n" + json.dumps(RECORDS[1]) + "\n",
            encoding="utf-8",
        )
        with self.assertRaisesRegex(CanonicalStoreInvalid, "multiple CURRENT revisions"):
            ReadOnlyCanonicalRepository(bad_store)

    def test_authority_store_is_logged_without_using_a_file_log(self) -> None:
        with self.assertLogs("master_brain_bridge.repository", level=logging.INFO) as captured:
            self.repository().get("MBK-VOX-ARCHITECTURE-01KTEST0002")
        event = " ".join(captured.output)
        self.assertIn("authority=MASTER_BRAIN_CANONICAL_STORE", event)
        self.assertIn("store_id=acceptance-fixture", event)

    def test_bridge_has_no_dependency_on_wrong_empty_docker_mount(self) -> None:
        os.environ["OBSIDIAN_VAULT_PATH"] = str(self.wrong_docker_mount)
        try:
            result = self.repository().get("MBK-VOX-ARCHITECTURE-01KTEST0002")
        finally:
            os.environ.pop("OBSIDIAN_VAULT_PATH", None)
        self.assertEqual(result["canonical_status"], "CURRENT")
        self.assertEqual(list(self.wrong_docker_mount.iterdir()), [])


if __name__ == "__main__":
    unittest.main()

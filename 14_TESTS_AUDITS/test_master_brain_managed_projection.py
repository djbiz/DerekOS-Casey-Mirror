"""Acceptance tests for Slice 2 managed projection publisher."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge import (
    CanonicalRecordInvalid,
    ManagedProjectionPublisher,
    PathCollisionError,
    ReadOnlyCanonicalRepository,
    UnauthorizedWriteError,
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
        "approval_status": "ACCEPTED",
        "projection_policy": "PUBLISH",
    },
    {
        "knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
        "revision": 2,
        "canonical_status": "CURRENT",
        "title": "Three-temperature knowledge ownership",
        "summary": "Master Brain owns canon, Obsidian is warm, and VOX is hot.",
        "content": "Historical truth belongs to Master Brain; live operations belong to VOX.",
        "evidence_ids": ["evidence-message-001", "evidence-board-002"],
        "approval_status": "ACCEPTED",
        "projection_policy": "PUBLISH",
    },
    {
        "knowledge_id": "MBK-VOX-ARCHITECTURE-01KTEST0002",
        "revision": 1,
        "canonical_status": "CURRENT",
        "title": "Advisory authority boundary",
        "summary": "Advisors propose work and do not authorize execution.",
        "content": "Execution authority remains external to the advisory envelope.",
        "evidence_ids": ["evidence-board-003"],
        "approval_status": "ACCEPTED",
        "projection_policy": "PUBLISH",
    },
]


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        digest.update(path.relative_to(root).as_posix().encode())
        if path.is_file():
            digest.update(path.read_bytes())
    return digest.hexdigest()


class ManagedProjectionAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = self.root / "canonical_records.jsonl"
        self.store.write_text("".join(json.dumps(record) + "\n" for record in RECORDS), encoding="utf-8")
        self.vault = self.root / "vault"
        self.vault.mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def repository(self) -> ReadOnlyCanonicalRepository:
        return ReadOnlyCanonicalRepository(self.store, store_id="projection-acceptance")

    def publisher(self) -> ManagedProjectionPublisher:
        return ManagedProjectionPublisher(self.repository(), self.vault)

    def test_first_publish_creates_managed_note(self) -> None:
        publisher = self.publisher()
        receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")

        self.assertEqual(receipt["action"], "published")
        self.assertEqual(receipt["knowledge_id"], "MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(receipt["revision"], 2)
        self.assertEqual(receipt["canonical_status"], "CURRENT")
        self.assertEqual(receipt["projection_schema"], 1)
        self.assertEqual(receipt["source_authority"], "MASTER_BRAIN_CANONICAL_STORE")

        note_path = self.vault / receipt["projection_path"]
        self.assertTrue(note_path.exists())

        content = note_path.read_text(encoding="utf-8")
        self.assertIn("master_brain_managed: true", content)
        self.assertIn("knowledge_id: MBK-DEREKOS-DECISION-01KTEST0001", content)
        self.assertIn("canonical_revision: 2", content)
        self.assertIn("canonical_status: current", content)
        self.assertIn("projection_schema: 1", content)
        self.assertIn("source_authority: MASTER_BRAIN_CANONICAL_STORE", content)
        self.assertIn("approval_status: accepted", content)
        self.assertIn("projection_policy: publish", content)
        self.assertIn("managed projection", content.lower())

    def test_no_op_republish_when_revision_unchanged(self) -> None:
        publisher = self.publisher()
        first_receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")
        note_path = self.vault / first_receipt["projection_path"]
        first_mtime = note_path.stat().st_mtime

        import time
        time.sleep(0.01)

        second_receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")

        self.assertEqual(second_receipt["action"], "no_op")
        self.assertEqual(second_receipt["canonical_hash"], first_receipt["canonical_hash"])
        second_mtime = note_path.stat().st_mtime
        self.assertEqual(first_mtime, second_mtime, "note should not be rewritten on no-op")

    def test_revision_update_rewrites_note(self) -> None:
        original_store = self.root / "original_current.jsonl"
        original_record = dict(RECORDS[0], canonical_status="CURRENT")
        original_store.write_text(json.dumps(original_record) + "\n", encoding="utf-8")
        original_publisher = ManagedProjectionPublisher(
            ReadOnlyCanonicalRepository(original_store, store_id="original-current"), self.vault
        )
        first_receipt = original_publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(first_receipt["revision"], 1)
        self.assertEqual(first_receipt["canonical_status"], "CURRENT")

        publisher = self.publisher()
        second_receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001", revision=2)
        self.assertEqual(second_receipt["revision"], 2)
        self.assertEqual(second_receipt["canonical_status"], "CURRENT")
        self.assertNotEqual(first_receipt["canonical_hash"], second_receipt["canonical_hash"])

        note_path = self.vault / second_receipt["projection_path"]
        content = note_path.read_text(encoding="utf-8")
        self.assertIn("canonical_revision: 2", content)
        self.assertIn("canonical_status: current", content)

    def test_superseded_record_cannot_be_published(self) -> None:
        publisher = self.publisher()
        publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001", revision=2)

        with self.assertRaisesRegex(CanonicalRecordInvalid, "CURRENT"):
            publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001", revision=1)

        note_path = self.vault / "MasterBrain" / "Published" / "MBK-DEREKOS-DECISION-01KTEST0001.md"
        content = note_path.read_text(encoding="utf-8")
        self.assertIn("canonical_status: current", content)
        self.assertIn("canonical_revision: 2", content)

    def test_unapproved_record_cannot_be_published(self) -> None:
        store = self.root / "unapproved.jsonl"
        record = dict(RECORDS[2], approval_status="PENDING")
        store.write_text(json.dumps(record) + "\n", encoding="utf-8")
        publisher = ManagedProjectionPublisher(ReadOnlyCanonicalRepository(store), self.vault)
        with self.assertRaisesRegex(CanonicalRecordInvalid, "ACCEPTED"):
            publisher.publish(record["knowledge_id"])
        self.assertFalse((self.vault / "MasterBrain").exists())

    def test_human_edit_to_managed_body_blocks_update(self) -> None:
        publisher = self.publisher()
        receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")
        note_path = self.vault / receipt["projection_path"]
        note_path.write_text(note_path.read_text(encoding="utf-8") + "human edit\n", encoding="utf-8")
        with self.assertRaisesRegex(PathCollisionError, "out-of-band"):
            publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")

    def test_malformed_canonical_input_fails_visible(self) -> None:
        from master_brain_bridge import CanonicalStoreInvalid
        bad_store = self.root / "bad_records.jsonl"
        bad_record = {
            "knowledge_id": "",
            "revision": 1,
            "canonical_status": "CURRENT",
            "title": "Empty ID",
            "content": "Bad record",
            "evidence_ids": [],
        }
        bad_store.write_text(json.dumps(bad_record) + "\n", encoding="utf-8")
        with self.assertRaises(CanonicalStoreInvalid):
            ReadOnlyCanonicalRepository(bad_store)

    def test_path_collision_with_human_authored_note(self) -> None:
        managed_dir = self.vault / "MasterBrain" / "Published"
        managed_dir.mkdir(parents=True)

        knowledge_id = "MBK-DEREKOS-DECISION-01KTEST0001"
        expected_filename = f"{knowledge_id}.md"
        human_note = managed_dir / expected_filename
        human_note.write_text("# Human Note\n\nThis is human-authored.", encoding="utf-8")

        collision_repo = ReadOnlyCanonicalRepository(self.store, store_id="collision-test")
        collision_publisher = ManagedProjectionPublisher(collision_repo, self.vault)

        with self.assertRaises(PathCollisionError) as ctx:
            collision_publisher.publish(knowledge_id)
        self.assertIn("human-authored note exists", str(ctx.exception))

    def test_unauthorized_write_outside_managed_subtree(self) -> None:
        repo = self.repository()
        with self.assertRaises(UnauthorizedWriteError):
            ManagedProjectionPublisher(repo, self.vault, projection_subtree="../../outside")

    def test_unsafe_knowledge_id_is_rejected_not_sanitized(self) -> None:
        unsafe_store = self.root / "unsafe.jsonl"
        unsafe_record = dict(RECORDS[2], knowledge_id="MBK-VOX-../ESCAPE")
        unsafe_store.write_text(json.dumps(unsafe_record) + "\n", encoding="utf-8")
        publisher = ManagedProjectionPublisher(ReadOnlyCanonicalRepository(unsafe_store), self.vault)
        with self.assertRaisesRegex(CanonicalRecordInvalid, "unsafe"):
            publisher.publish(unsafe_record["knowledge_id"])
        self.assertFalse((self.vault / "MasterBrain").exists())

    def test_provenance_metadata_preserved_in_note(self) -> None:
        publisher = self.publisher()
        receipt = publisher.publish("MBK-VOX-ARCHITECTURE-01KTEST0002")

        note_path = self.vault / receipt["projection_path"]
        content = note_path.read_text(encoding="utf-8")

        self.assertIn("knowledge_id: MBK-VOX-ARCHITECTURE-01KTEST0002", content)
        self.assertIn("canonical_revision: 1", content)
        self.assertIn("evidence-board-003", content)
        self.assertIn("**Knowledge ID:** MBK-VOX-ARCHITECTURE-01KTEST0002", content)
        self.assertIn("**Revision:** 1", content)
        self.assertIn("**Evidence IDs:** evidence-board-003", content)

    def test_no_writes_outside_managed_subtree(self) -> None:
        publisher = self.publisher()
        publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")
        publisher.publish("MBK-VOX-ARCHITECTURE-01KTEST0002")

        managed_dir = self.vault / "MasterBrain" / "Published"
        self.assertTrue(managed_dir.exists())

        for item in self.vault.rglob("*"):
            if item.is_file():
                relative = item.relative_to(self.vault).as_posix()
                self.assertTrue(
                    relative.startswith("MasterBrain/Published/"),
                    f"file written outside managed subtree: {relative}",
                )

    def test_publish_all_current_publishes_only_current_records(self) -> None:
        publisher = self.publisher()
        receipts = publisher.publish_all_current()

        current_ids = {r["knowledge_id"] for r in receipts if r["canonical_status"] == "CURRENT"}
        self.assertIn("MBK-DEREKOS-DECISION-01KTEST0001", current_ids)
        self.assertIn("MBK-VOX-ARCHITECTURE-01KTEST0002", current_ids)

        for receipt in receipts:
            self.assertEqual(receipt["canonical_status"], "CURRENT")

    def test_projection_is_logged(self) -> None:
        with self.assertLogs("master_brain_bridge.publisher", level=logging.INFO) as captured:
            publisher = self.publisher()
            publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")
        event = " ".join(captured.output)
        self.assertIn("operation=publish", event)
        self.assertIn("knowledge_id=MBK-DEREKOS-DECISION-01KTEST0001", event)
        self.assertIn("revision=2", event)

    def test_managed_note_has_explicit_non_authoritative_marker(self) -> None:
        publisher = self.publisher()
        receipt = publisher.publish("MBK-DEREKOS-DECISION-01KTEST0001")

        note_path = self.vault / receipt["projection_path"]
        content = note_path.read_text(encoding="utf-8")

        self.assertIn("managed projection", content.lower())
        self.assertIn("not the authoritative source", content.lower())
        self.assertIn("edits require candidate review", content.lower())


if __name__ == "__main__":
    unittest.main()

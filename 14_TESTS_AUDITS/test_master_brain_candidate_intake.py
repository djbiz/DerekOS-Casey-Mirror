"""Acceptance tests for Slice 3 candidate intake."""

from __future__ import annotations

import hashlib
import json
import logging
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge import (
    CandidateIntake,
    CandidatePathError,
    CandidateSourceInvalid,
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


class CandidateIntakeAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = self.root / "canonical_records.jsonl"
        self.store.write_text("".join(json.dumps(record) + "\n" for record in RECORDS), encoding="utf-8")
        self.vault = self.root / "vault"
        self.vault.mkdir()
        self.candidates_dir = self.vault / "MasterBrain" / "Candidates"
        self.candidates_dir.mkdir(parents=True)
        self.published_dir = self.vault / "MasterBrain" / "Published"
        self.published_dir.mkdir(parents=True)
        self.queue_path = self.root / "candidate_queue.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def repository(self) -> ReadOnlyCanonicalRepository:
        return ReadOnlyCanonicalRepository(self.store, store_id="intake-acceptance")

    def intake(self, *, repository: ReadOnlyCanonicalRepository | None = None) -> CandidateIntake:
        repo = repository if repository is not None else self.repository()
        return CandidateIntake(self.vault, self.queue_path, repository=repo)

    def test_new_candidate_creates_record(self) -> None:
        candidate_note = self.candidates_dir / "new-idea.md"
        candidate_note.write_text(
            "---\nproposed_operation: CREATE\nsubmitter: human\n---\n\n"
            "# New Strategy Idea\n\nWe should acquire three logistics companies.\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertTrue(record["candidate_id"].startswith("MBC-"))
        self.assertEqual(record["source_path"], "MasterBrain/Candidates/new-idea.md")
        self.assertEqual(len(record["source_hash"]), 64)
        self.assertEqual(record["proposed_operation"], "CREATE")
        self.assertEqual(record["submitter"], "human")
        self.assertEqual(record["status"], "SUBMITTED")
        self.assertEqual(record["candidate_revision"], 1)
        self.assertEqual(record["source_system"], "obsidian")
        self.assertEqual(record["intake_schema"], 1)
        self.assertIsNone(record["proposed_knowledge_id"])
        self.assertIsNone(record["base_canonical_revision"])

        self.assertTrue(self.queue_path.exists())
        queue_content = self.queue_path.read_text(encoding="utf-8")
        self.assertIn(record["candidate_id"], queue_content)

    def test_duplicate_candidate_is_idempotent(self) -> None:
        candidate_note = self.candidates_dir / "duplicate-test.md"
        candidate_note.write_text("# Same Content\n", encoding="utf-8")

        intake = self.intake()
        first = intake.ingest(candidate_note)
        second = intake.ingest(candidate_note)

        self.assertEqual(first["candidate_id"], second["candidate_id"])
        self.assertEqual(first["source_hash"], second["source_hash"])

        queue_lines = [line for line in self.queue_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(queue_lines), 1, "duplicate ingest must not create a second queue entry")

    def test_candidate_update_with_changed_content(self) -> None:
        candidate_note = self.candidates_dir / "update-test.md"
        candidate_note.write_text("# Version 1\n", encoding="utf-8")

        intake = self.intake()
        first = intake.ingest(candidate_note)

        candidate_note.write_text("# Version 2 - updated\n", encoding="utf-8")
        second = intake.ingest(candidate_note)

        self.assertNotEqual(first["source_hash"], second["source_hash"])
        self.assertEqual(first["candidate_id"], second["candidate_id"])
        self.assertEqual(second["candidate_revision"], 2)

        queue_lines = [line for line in self.queue_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(queue_lines), 2)

    def test_candidate_against_current_canonical_revision(self) -> None:
        candidate_note = self.candidates_dir / "current-revision.md"
        candidate_note.write_text(
            "---\nproposed_knowledge_id: MBK-DEREKOS-DECISION-01KTEST0001\n"
            "proposed_operation: UPDATE\nbase_canonical_revision: 2\n---\n\n"
            "# Updated Knowledge\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["proposed_knowledge_id"], "MBK-DEREKOS-DECISION-01KTEST0001")
        self.assertEqual(record["base_canonical_revision"], 2)
        self.assertEqual(record["proposed_operation"], "UPDATE")
        self.assertEqual(record["status"], "REVIEW_READY")

    def test_candidate_against_stale_revision_becomes_conflict(self) -> None:
        candidate_note = self.candidates_dir / "stale-revision.md"
        candidate_note.write_text(
            "---\nproposed_knowledge_id: MBK-DEREKOS-DECISION-01KTEST0001\n"
            "proposed_operation: UPDATE\nbase_canonical_revision: 1\n---\n\n"
            "# Stale Update\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["base_canonical_revision"], 1)
        self.assertEqual(record["status"], "CONFLICT_OPEN")

    def test_unknown_knowledge_id_stays_pending(self) -> None:
        candidate_note = self.candidates_dir / "unknown-id.md"
        candidate_note.write_text(
            "---\nproposed_knowledge_id: MBK-NONEXISTENT-000\n"
            "proposed_operation: UPDATE\n---\n\n"
            "# Unknown Reference\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["proposed_knowledge_id"], "MBK-NONEXISTENT-000")
        self.assertEqual(record["status"], "SUBMITTED")

    def test_malformed_metadata_defaults_gracefully(self) -> None:
        candidate_note = self.candidates_dir / "malformed.md"
        candidate_note.write_text(
            "---\nproposed_operation: INVALID_OP\n"
            "base_canonical_revision: not_a_number\n"
            "candidate_type: WHATEVER\n---\n\n"
            "# Malformed Metadata\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["proposed_operation"], "UNKNOWN")
        self.assertIsNone(record["base_canonical_revision"])
        self.assertEqual(record["candidate_type"], "UNKNOWN")
        self.assertEqual(record["status"], "SUBMITTED")

    def test_path_traversal_rejected(self) -> None:
        outside_note = self.root / "outside_vault.md"
        outside_note.write_text("# Outside\n", encoding="utf-8")

        intake = self.intake()
        with self.assertRaises(CandidatePathError):
            intake.ingest(outside_note)

    def test_path_traversal_via_dotdot_rejected(self) -> None:
        traversal_path = self.candidates_dir / ".." / ".." / "outside_vault.md"
        outside_note = self.root / "outside_vault.md"
        outside_note.write_text("# Outside\n", encoding="utf-8")

        intake = self.intake()
        with self.assertRaises(CandidatePathError):
            intake.ingest(traversal_path)

    def test_published_projection_rejected_as_candidate(self) -> None:
        published_note = self.published_dir / "MBK-DEREKOS-DECISION-01KTEST0001.md"
        published_note.write_text(
            "---\nmaster_brain_managed: true\nknowledge_id: MBK-DEREKOS-DECISION-01KTEST0001\n---\n\n"
            "# Managed Projection\n",
            encoding="utf-8",
        )

        intake = self.intake()
        with self.assertRaises(CandidatePathError):
            intake.ingest(published_note)

    def test_intake_does_not_modify_canonical_store(self) -> None:
        store_before = self.store.read_bytes()

        candidate_note = self.candidates_dir / "non-destructive.md"
        candidate_note.write_text("# Non-Destructive Test\n", encoding="utf-8")

        intake = self.intake()
        intake.ingest(candidate_note)

        store_after = self.store.read_bytes()
        self.assertEqual(store_before, store_after, "canonical store must not be modified by intake")

    def test_candidate_with_provenance_references(self) -> None:
        candidate_note = self.candidates_dir / "with-provenance.md"
        candidate_note.write_text(
            "---\nproposed_operation: CREATE\n"
            "provenance_refs: evidence-message-001, evidence-board-002\n"
            "submitter: derek\n---\n\n"
            "# Evidence-Backed Proposal\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["provenance_refs"], ["evidence-message-001", "evidence-board-002"])
        self.assertEqual(record["submitter"], "human")
        self.assertEqual(record["claimed_submitter"], "derek")

    def test_candidate_with_list_provenance_references(self) -> None:
        candidate_note = self.candidates_dir / "with-list-provenance.md"
        candidate_note.write_text(
            "---\nproposed_operation: CREATE\n"
            "evidence_refs: evidence-001, evidence-002\n---\n\n"
            "# Evidence-Backed Proposal\n",
            encoding="utf-8",
        )

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["provenance_refs"], ["evidence-001", "evidence-002"])

    def test_empty_canonical_store_still_intakes(self) -> None:
        empty_store = self.root / "empty_canonical.jsonl"
        empty_store.write_text(
            json.dumps({
                "knowledge_id": "MBK-MINIMAL-01KTEST9999",
                "revision": 1,
                "canonical_status": "CURRENT",
                "title": "Minimal",
                "content": "Minimal record.",
                "evidence_ids": [],
            }) + "\n",
            encoding="utf-8",
        )
        empty_repo = ReadOnlyCanonicalRepository(empty_store)

        candidate_note = self.candidates_dir / "no-canonical.md"
        candidate_note.write_text(
            "---\nproposed_knowledge_id: MBK-NOT-IN-STORE-000\n"
            "proposed_operation: CREATE\n---\n\n"
            "# New Knowledge\n",
            encoding="utf-8",
        )

        intake = CandidateIntake(self.vault, self.queue_path, repository=empty_repo)
        record = intake.ingest(candidate_note)

        self.assertEqual(record["status"], "SUBMITTED")
        self.assertEqual(record["proposed_operation"], "CREATE")

    def test_intake_does_not_modify_published_or_vault(self) -> None:
        candidate_note = self.candidates_dir / "non-destructive-2.md"
        candidate_note.write_text("# Non-Destructive\n", encoding="utf-8")

        before_vault = tree_digest(self.vault)

        intake = self.intake()
        intake.ingest(candidate_note)

        after_vault = tree_digest(self.vault)
        self.assertEqual(before_vault, after_vault, "intake must not modify any vault content")

    def test_intake_is_logged(self) -> None:
        candidate_note = self.candidates_dir / "logged.md"
        candidate_note.write_text("# Logged Test\n", encoding="utf-8")

        with self.assertLogs("master_brain_bridge.candidate_intake", level=logging.INFO) as captured:
            intake = self.intake()
            intake.ingest(candidate_note)
        event = " ".join(captured.output)
        self.assertIn("operation=ingest", event)
        self.assertIn("source=MasterBrain/Candidates/logged.md", event)

    def test_ingest_all_scans_candidates_directory(self) -> None:
        (self.candidates_dir / "first.md").write_text("# First\n", encoding="utf-8")
        (self.candidates_dir / "second.md").write_text("# Second\n", encoding="utf-8")
        (self.candidates_dir / "third.md").write_text("# Third\n", encoding="utf-8")

        intake = self.intake()
        records = intake.ingest_all()

        self.assertEqual(len(records), 3)
        source_paths = {r["source_path"] for r in records}
        self.assertIn("MasterBrain/Candidates/first.md", source_paths)
        self.assertIn("MasterBrain/Candidates/second.md", source_paths)
        self.assertIn("MasterBrain/Candidates/third.md", source_paths)

    def test_ingest_all_ignores_non_markdown_files(self) -> None:
        (self.candidates_dir / "valid.md").write_text("# Valid\n", encoding="utf-8")
        (self.candidates_dir / "ignore.txt").write_text("ignore me\n", encoding="utf-8")
        (self.candidates_dir / "ignore.json").write_text("{}", encoding="utf-8")

        intake = self.intake()
        records = intake.ingest_all()

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["source_path"], "MasterBrain/Candidates/valid.md")

    def test_no_frontmatter_candidate_still_intakes(self) -> None:
        candidate_note = self.candidates_dir / "no-frontmatter.md"
        candidate_note.write_text("# Just a Raw Note\n\nWith some content.\n", encoding="utf-8")

        intake = self.intake()
        record = intake.ingest(candidate_note)

        self.assertEqual(record["proposed_operation"], "UNKNOWN")
        self.assertEqual(record["candidate_type"], "UNKNOWN")
        self.assertEqual(record["status"], "SUBMITTED")
        self.assertIsNone(record["proposed_knowledge_id"])
        self.assertIn("Just a Raw Note", record["content_summary"])

    def test_note_cannot_self_declare_accepted(self) -> None:
        candidate_note = self.candidates_dir / "self-approved.md"
        candidate_note.write_text("---\nstatus: ACCEPTED\n---\n\n# Unreviewed\n", encoding="utf-8")
        record = self.intake().ingest(candidate_note)
        self.assertEqual(record["status"], "SUBMITTED")

    def test_identical_content_at_different_paths_is_not_collapsed(self) -> None:
        first_path = self.candidates_dir / "first-copy.md"
        second_path = self.candidates_dir / "second-copy.md"
        first_path.write_text("# Same\n", encoding="utf-8")
        second_path.write_text("# Same\n", encoding="utf-8")
        intake = self.intake()
        first = intake.ingest(first_path)
        second = intake.ingest(second_path)
        self.assertNotEqual(first["candidate_id"], second["candidate_id"])


if __name__ == "__main__":
    unittest.main()

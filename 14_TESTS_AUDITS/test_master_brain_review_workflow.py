"""Acceptance tests for Slice 4 review/commit workflow."""

from __future__ import annotations

import json
import hashlib
import logging
import tempfile
import unittest
from pathlib import Path

from master_brain_bridge import (
    ApprovalInvalid,
    CanonicalCommitError,
    CandidateNotFound,
    FounderApprovalRequired,
    ReadOnlyCanonicalRepository,
    ReviewWorkflow,
    ReviewError,
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


def write_queue(path: Path, candidates: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = []
    status_map = {"PENDING": "SUBMITTED", "READY_FOR_REVIEW": "REVIEW_READY", "CONFLICT": "CONFLICT_OPEN"}
    for source in candidates:
        candidate = dict(source)
        content = candidate.get("content", candidate.get("content_summary", ""))
        candidate.setdefault("candidate_revision", 1)
        candidate.setdefault("submitter", "human")
        candidate["content"] = content
        candidate["content_hash"] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        candidate["status"] = status_map.get(candidate.get("status"), candidate.get("status"))
        candidate.setdefault("evidence_ids", candidate.get("provenance_refs", []))
        normalized.append(candidate)
    path.write_text("".join(json.dumps(c) + "\n" for c in normalized), encoding="utf-8")


def approval(review: dict, *, authority: str = "KNOWLEDGE_CURATOR", approver: str = "derek") -> dict:
    return {
        "approval_id": f"APR-{review['review_id']}",
        "review_id": review["review_id"],
        "approver_identity": approver,
        "authority": authority,
        "decision": "APPROVE",
        "issued_at": "2026-08-12T15:00:00Z",
    }


class ReviewWorkflowAcceptanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.store = self.root / "canonical_records.jsonl"
        self.store.write_text("".join(json.dumps(r) + "\n" for r in RECORDS), encoding="utf-8")
        self.queue_path = self.root / "candidate_queue.jsonl"
        self.review_log_path = self.root / "review_log.jsonl"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def repository(self) -> ReadOnlyCanonicalRepository:
        return ReadOnlyCanonicalRepository(self.store, store_id="review-acceptance")

    def workflow(self) -> ReviewWorkflow:
        return ReviewWorkflow(
            self.repository(),
            self.queue_path,
            self.review_log_path,
            verified_evidence_ids={
                "evidence-message-001", "evidence-board-002", "evidence-board-003",
                "evidence-new-001", "evidence-new-idea-001", "evidence-supersede-001",
                "evidence-hist-001",
            },
            approval_verifier=lambda artifact: artifact.get("approval_id", "").startswith("APR-"),
        )

    def test_exact_duplicate_classification(self) -> None:
        candidate = {
            "candidate_id": "MBC-DUP001",
            "source_hash": "abc123",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Historical truth belongs to Master Brain; live operations belong to VOX.",
            "content_hash": "def456",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-DUP001")

        self.assertEqual(review["classification"], "DUPLICATE")
        self.assertEqual(review["commit_proposal"]["action"], "NO_COMMIT")
        self.assertGreater(review["confidence"], 0.9)
        self.assertFalse(review["founder_approval_required"])

    def test_reaffirmation_classification(self) -> None:
        candidate = {
            "candidate_id": "MBC-REA001",
            "source_hash": "abc124",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Master Brain owns canon Obsidian is warm and VOX is hot.",
            "content_hash": "def457",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-REA001")

        self.assertEqual(review["classification"], "REAFFIRMATION")
        self.assertEqual(review["commit_proposal"]["action"], "NO_COMMIT")
        self.assertGreater(review["confidence"], 0.8)

    def test_safe_update_classification(self) -> None:
        candidate = {
            "candidate_id": "MBC-UPD001",
            "source_hash": "abc125",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Updated understanding with new evidence about knowledge temperatures.",
            "content_hash": "def458",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-new-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-UPD001")

        self.assertEqual(review["classification"], "UPDATE")
        self.assertEqual(review["commit_proposal"]["action"], "UPDATE")
        self.assertEqual(review["commit_proposal"]["proposed_revision"], 3)
        self.assertIn("evidence-new-001", review["supporting_evidence_ids"])

    def test_stale_base_update_becomes_conflict(self) -> None:
        candidate = {
            "candidate_id": "MBC-STALE001",
            "source_hash": "abc126",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 1,
            "content_summary": "Update based on stale revision 1.",
            "content_hash": "def459",
            "status": "CONFLICT",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-STALE001")

        self.assertEqual(review["classification"], "CONFLICT")
        self.assertEqual(review["commit_proposal"]["action"], "DEFER")
        self.assertTrue(review["founder_approval_required"])
        self.assertIsNotNone(review["conflict_packet"])
        self.assertTrue(review["conflict_packet"]["founder_decision_required"])

    def test_supersession_classification(self) -> None:
        candidate = {
            "candidate_id": "MBC-SUP001",
            "source_hash": "abc127",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "SUPERSEDE",
            "base_canonical_revision": 2,
            "content_summary": "Completely new model replaces three-temperature ownership.",
            "content_hash": "def460",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-supersede-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-SUP001")

        self.assertEqual(review["classification"], "SUPERSESSION")
        self.assertEqual(review["commit_proposal"]["action"], "SUPERSEDE")
        self.assertEqual(review["commit_proposal"]["supersedes_revision"], 2)
        self.assertEqual(review["commit_proposal"]["proposed_revision"], 3)
        self.assertTrue(review["founder_approval_required"])

    def test_retirement_request(self) -> None:
        candidate = {
            "candidate_id": "MBC-RET001",
            "source_hash": "abc128",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "RETIRE",
            "base_canonical_revision": 2,
            "content_summary": "This knowledge is no longer relevant.",
            "content_hash": "def461",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-hist-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-RET001")

        self.assertEqual(review["classification"], "RETIREMENT")
        self.assertEqual(review["commit_proposal"]["action"], "RETIRE")
        self.assertTrue(review["founder_approval_required"])

    def test_insufficient_evidence(self) -> None:
        candidate = {
            "candidate_id": "MBC-INS001",
            "source_hash": "abc129",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UNKNOWN",
            "content_summary": "Vague proposal with no clear operation.",
            "content_hash": "def462",
            "status": "PENDING",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-INS001")

        self.assertEqual(review["classification"], "INSUFFICIENT_EVIDENCE")
        self.assertEqual(review["commit_proposal"]["action"], "NO_COMMIT")
        self.assertLess(review["confidence"], 0.5)

    def test_unknown_knowledge_id_becomes_new_knowledge(self) -> None:
        candidate = {
            "candidate_id": "MBC-NEW001",
            "source_hash": "abc130",
            "proposed_knowledge_id": None,
            "proposed_operation": "CREATE",
            "content_summary": "Brand new knowledge about corporate academy training.",
            "content_hash": "def463",
            "status": "PENDING",
            "provenance_refs": ["evidence-new-idea-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-NEW001")

        self.assertEqual(review["classification"], "NEW_KNOWLEDGE")
        self.assertEqual(review["commit_proposal"]["action"], "CREATE")
        self.assertEqual(review["commit_proposal"]["proposed_revision"], 1)

    def test_malformed_candidate_is_rejected(self) -> None:
        candidate = {
            "candidate_id": "MBC-MAL001",
            "source_hash": "abc131",
            "content_summary": "Malformed candidate with missing fields.",
            "content_hash": "def464",
            "status": "PENDING",
        }
        self.queue_path.write_text(json.dumps(candidate) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ReviewError, "candidate contract missing"):
            self.workflow().review_candidate("MBC-MAL001")

    def test_review_does_not_mutate_canonical_store(self) -> None:
        store_before = self.store.read_bytes()

        candidate = {
            "candidate_id": "MBC-NOMUT001",
            "source_hash": "abc132",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Proposed update that should not execute.",
            "content_hash": "def465",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-supersede-001"],
        }
        write_queue(self.queue_path, [candidate])

        self.workflow().review_candidate("MBC-NOMUT001")

        store_after = self.store.read_bytes()
        self.assertEqual(store_before, store_after, "review must not mutate canonical store")

    def test_founder_required_decision(self) -> None:
        candidate = {
            "candidate_id": "MBC-FOU001",
            "source_hash": "abc133",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "SUPERSEDE",
            "base_canonical_revision": 2,
            "content_summary": "Major strategy change requiring founder approval.",
            "content_hash": "def466",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-supersede-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-FOU001")

        self.assertTrue(review["founder_approval_required"])

        with self.assertRaises(FounderApprovalRequired):
            self.workflow().propose_canonical_commit(
                review["review_id"],
                approval_record=approval(review, authority="KNOWLEDGE_CURATOR"),
            )

        commit = self.workflow().propose_canonical_commit(
            review["review_id"],
            approval_record=approval(review, authority="FOUNDER"),
        )
        self.assertEqual(commit["review_id"], review["review_id"])
        self.assertEqual(commit["execution_status"], "NOT_EXECUTED")

    def test_accepted_revision_preserves_history(self) -> None:
        candidate = {
            "candidate_id": "MBC-HIST001",
            "source_hash": "abc134",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Update that preserves revision history.",
            "content_hash": "def467",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-hist-001"],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-HIST001")
        commit = self.workflow().propose_canonical_commit(
            review["review_id"],
            approval_record=approval(review, authority="FOUNDER"),
        )

        self.assertEqual(commit["proposed_revision"], 3)
        self.assertEqual(review["current_canonical_revision"], 2)
        self.assertEqual(review["classification"], "UPDATE")

    def test_rejected_candidate_remains_auditable(self) -> None:
        candidate = {
            "candidate_id": "MBC-REJ001",
            "source_hash": "abc135",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Rejected candidate that should remain in review log.",
            "content_hash": "def468",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        review = self.workflow().review_candidate("MBC-REJ001")

        self.assertTrue(self.review_log_path.exists())
        review_log = self.review_log_path.read_text(encoding="utf-8")
        self.assertIn("MBC-REJ001", review_log)
        self.assertIn(review["review_id"], review_log)

    def test_review_all_pending(self) -> None:
        candidates = [
            {
                "candidate_id": "MBC-BATCH001",
                "source_hash": "abc136",
                "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
                "proposed_operation": "UPDATE",
                "base_canonical_revision": 2,
                "content_summary": "First pending candidate.",
                "content_hash": "def469",
                "status": "PENDING",
                "provenance_refs": [],
            },
            {
                "candidate_id": "MBC-BATCH002",
                "source_hash": "abc137",
                "proposed_knowledge_id": None,
                "proposed_operation": "CREATE",
                "content_summary": "Second pending candidate.",
                "content_hash": "def470",
                "status": "READY_FOR_REVIEW",
                "provenance_refs": [],
            },
        ]
        write_queue(self.queue_path, candidates)

        reviews = self.workflow().review_all_pending()

        self.assertEqual(len(reviews), 2)
        review_ids = {r["candidate_id"] for r in reviews}
        self.assertIn("MBC-BATCH001", review_ids)
        self.assertIn("MBC-BATCH002", review_ids)

    def test_review_is_logged(self) -> None:
        candidate = {
            "candidate_id": "MBC-LOG001",
            "source_hash": "abc138",
            "proposed_knowledge_id": "MBK-DEREKOS-DECISION-01KTEST0001",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 2,
            "content_summary": "Logged review test.",
            "content_hash": "def471",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": [],
        }
        write_queue(self.queue_path, [candidate])

        with self.assertLogs("master_brain_bridge.review_workflow", level=logging.INFO) as captured:
            self.workflow().review_candidate("MBC-LOG001")
        event = " ".join(captured.output)
        self.assertIn("classification=UPDATE", event)
        self.assertIn("candidate_id=MBC-LOG001", event)

    def test_boolean_or_incomplete_approval_cannot_authorize_change(self) -> None:
        candidate = {
            "candidate_id": "MBC-APPROVAL001",
            "source_hash": "source-approval",
            "proposed_knowledge_id": "MBK-VOX-ARCHITECTURE-01KTEST0002",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 1,
            "content_summary": "A verified update requiring a real approval artifact.",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-new-001"],
        }
        write_queue(self.queue_path, [candidate])
        review = self.workflow().review_candidate(candidate["candidate_id"])
        with self.assertRaises(ApprovalInvalid):
            self.workflow().propose_canonical_commit(review["review_id"], approval_record={"founder_approved": True})

    def test_reviewer_cannot_review_own_candidate(self) -> None:
        candidate = {
            "candidate_id": "MBC-SELF001",
            "source_hash": "source-self",
            "proposed_knowledge_id": None,
            "proposed_operation": "CREATE",
            "content_summary": "Self reviewed proposal.",
            "status": "PENDING",
            "provenance_refs": ["evidence-new-idea-001"],
            "submitter": "ai-reviewer",
        }
        write_queue(self.queue_path, [candidate])
        with self.assertRaisesRegex(ReviewError, "cannot review"):
            self.workflow().review_candidate(candidate["candidate_id"])

    def test_unverified_evidence_blocks_change_packet(self) -> None:
        candidate = {
            "candidate_id": "MBC-UNVERIFIED001",
            "source_hash": "source-unverified",
            "proposed_knowledge_id": "MBK-VOX-ARCHITECTURE-01KTEST0002",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 1,
            "content_summary": "Update supported only by an unverified citation.",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-unverified-999"],
        }
        write_queue(self.queue_path, [candidate])
        review = self.workflow().review_candidate(candidate["candidate_id"])
        self.assertEqual(review["commit_proposal"]["action"], "EVIDENCE_REQUIRED")
        with self.assertRaises(CanonicalCommitError):
            self.workflow().propose_canonical_commit(
                review["review_id"], approval_record=approval(review, authority="ARCHITECTURE_BOARD")
            )

    def test_no_approval_verifier_means_no_change_packet(self) -> None:
        candidate = {
            "candidate_id": "MBC-NOVERIFIER001",
            "source_hash": "source-no-verifier",
            "proposed_knowledge_id": "MBK-VOX-ARCHITECTURE-01KTEST0002",
            "proposed_operation": "UPDATE",
            "base_canonical_revision": 1,
            "content_summary": "Verified evidence but no approval verifier.",
            "status": "READY_FOR_REVIEW",
            "provenance_refs": ["evidence-new-001"],
        }
        write_queue(self.queue_path, [candidate])
        workflow = ReviewWorkflow(
            self.repository(), self.queue_path, self.review_log_path,
            verified_evidence_ids={"evidence-new-001"},
        )
        review = workflow.review_candidate(candidate["candidate_id"])
        with self.assertRaisesRegex(ApprovalInvalid, "could not be verified"):
            workflow.propose_canonical_commit(
                review["review_id"], approval_record=approval(review, authority="ARCHITECTURE_BOARD")
            )


if __name__ == "__main__":
    unittest.main()

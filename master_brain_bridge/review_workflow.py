"""Slice 4: Conflict / Review / Commit Workflow.

This module analyzes queued candidates, compares them against the canonical store,
classifies them, and produces review decisions with canonical commit proposals.
It may analyze, compare, and recommend, but it must NOT silently mutate canonical knowledge.
Founder approval is mandatory for high-risk changes.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .repository import ReadOnlyCanonicalRepository, CanonicalKnowledgeNotFound

LOGGER = logging.getLogger(__name__)

CLASSIFICATIONS = {
    "DUPLICATE",
    "REAFFIRMATION",
    "NEW_KNOWLEDGE",
    "UPDATE",
    "SUPERSESSION",
    "RETIREMENT",
    "CONFLICT",
    "INSUFFICIENT_EVIDENCE",
    "REJECTED",
}

FOUNDER_REQUIRED_DOMAINS = {
    "constitutional",
    "master-plan",
    "governance",
    "architecture-ownership",
    "major-strategy",
}
REVIEWABLE_STATUSES = {"SUBMITTED", "REVIEW_READY", "CONFLICT_OPEN"}
APPROVER_AUTHORITIES = {"FOUNDER", "ARCHITECTURE_BOARD", "KNOWLEDGE_CURATOR"}

AUTO_CLEAR_CLASSIFICATIONS = {"DUPLICATE", "REAFFIRMATION"}


class ReviewError(RuntimeError):
    """Base exception for review workflow failures."""


class CandidateNotFound(ReviewError):
    """The referenced candidate does not exist in the queue."""


class CanonicalCommitError(ReviewError):
    """The proposed canonical commit violates the versioning contract."""


class FounderApprovalRequired(ReviewError):
    """The proposed change requires founder approval before canonical commit."""


class ApprovalInvalid(ReviewError):
    """The supplied approval artifact is missing, malformed, or unauthorized."""


class ReviewWorkflow:
    """Analyzes candidates and produces review decisions with commit proposals.

    This workflow may analyze, compare, and recommend, but it does NOT silently
    mutate canonical knowledge. It produces commit proposals that require explicit
    approval before execution. Founder approval is mandatory for high-risk changes.
    """

    def __init__(
        self,
        repository: ReadOnlyCanonicalRepository,
        queue_path: str | os.PathLike[str],
        review_log_path: str | os.PathLike[str],
        *,
        reviewer_identity: str = "ai-reviewer",
        verified_evidence_ids: set[str] | None = None,
        approval_verifier: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        self._repository = repository
        self._queue_path = Path(queue_path).expanduser().resolve(strict=False)
        self._review_log_path = Path(review_log_path).expanduser().resolve(strict=False)
        if not isinstance(reviewer_identity, str) or not reviewer_identity.strip():
            raise ReviewError("reviewer_identity must be explicit")
        self._reviewer_identity = reviewer_identity.strip()
        self._verified_evidence_ids = frozenset(verified_evidence_ids or set())
        self._approval_verifier = approval_verifier

    @classmethod
    def from_environment(
        cls,
        repository: ReadOnlyCanonicalRepository,
        *,
        reviewer_identity: str = "ai-reviewer",
    ) -> "ReviewWorkflow":
        """Create the workflow from environment variables."""

        queue_path = os.getenv("MASTER_BRAIN_CANDIDATE_QUEUE_PATH")
        if not queue_path:
            repository_root = Path(__file__).resolve().parents[1]
            queue_path = repository_root / "12_CONFLICTS" / "candidate_queue.jsonl"
        review_log_path = os.getenv("MASTER_BRAIN_REVIEW_LOG_PATH")
        if not review_log_path:
            repository_root = Path(__file__).resolve().parents[1]
            review_log_path = repository_root / "12_CONFLICTS" / "review_log.jsonl"
        return cls(repository, queue_path, review_log_path, reviewer_identity=reviewer_identity)

    def review_candidate(self, candidate_id: str) -> dict[str, Any]:
        """Review one candidate and return the review decision.

        The review decision includes classification, evidence analysis, confidence,
        rationale, founder approval requirement, and a canonical commit proposal.
        The proposal does NOT execute; it requires explicit approval.
        """

        candidate = self._load_candidate(candidate_id)
        self._validate_candidate(candidate)
        classification = self._classify_candidate(candidate)
        evidence_analysis = self._analyze_evidence(candidate, classification)
        founder_required = self._requires_founder_approval(candidate, classification)
        commit_proposal = self._build_commit_proposal(candidate, classification, evidence_analysis)

        review = {
            "review_id": f"REV-{uuid.uuid4().hex[:16].upper()}",
            "candidate_id": candidate_id,
            "candidate_source_hash": candidate.get("source_hash"),
            "related_knowledge_id": candidate.get("proposed_knowledge_id"),
            "current_canonical_revision": evidence_analysis.get("current_revision"),
            "proposed_new_revision": commit_proposal.get("proposed_revision"),
            "classification": classification,
            "supporting_evidence_ids": evidence_analysis.get("supporting", []),
            "contradicting_evidence_ids": evidence_analysis.get("contradicting", []),
            "provenance_status": evidence_analysis.get("provenance_status", "UNVERIFIED"),
            "confidence": evidence_analysis.get("confidence", 0.0),
            "rationale": evidence_analysis.get("rationale", ""),
            "founder_approval_required": founder_required,
            "review_timestamp": datetime.now(timezone.utc).isoformat(),
            "reviewer_identity": self._reviewer_identity,
            "commit_proposal": commit_proposal,
            "conflict_packet": self._build_conflict_packet(candidate, classification, evidence_analysis) if classification == "CONFLICT" else None,
            "review_schema": 1,
        }

        self._append_review_log(review)
        self._log_review(review)
        return review

    def review_all_pending(self) -> list[dict[str, Any]]:
        """Review all governed intake-state candidates. Returns reviews."""

        reviews: list[dict[str, Any]] = []
        for candidate in self._load_all_candidates():
            if candidate.get("status") not in REVIEWABLE_STATUSES:
                continue
            try:
                review = self.review_candidate(candidate["candidate_id"])
                reviews.append(review)
            except ReviewError as exc:
                LOGGER.warning("review_all_pending skipped %s: %s", candidate.get("candidate_id"), exc)
        return reviews

    def propose_canonical_commit(self, review_id: str, *, approval_record: dict[str, Any]) -> dict[str, Any]:
        """Propose a canonical commit based on an approved review.

        This does NOT execute the commit. It returns a commit proposal that must be
        applied by a separate canonical commit service. Founder approval is enforced
        for high-risk changes.
        """

        review = self._load_review(review_id)
        approval = self._validate_approval(review, approval_record)
        proposal = review.get("commit_proposal")
        if not proposal:
            raise ReviewError(f"review {review_id} has no commit proposal")
        if proposal.get("action") in {"NO_COMMIT", "DEFER", "EVIDENCE_REQUIRED"}:
            raise CanonicalCommitError(f"review {review_id} is not eligible for a canonical change packet")
        commit = {
            "change_packet_id": f"CCP-{uuid.uuid4().hex[:16].upper()}",
            "review_id": review_id,
            "candidate_id": review["candidate_id"],
            "knowledge_id": proposal.get("knowledge_id"),
            "proposed_revision": proposal.get("proposed_revision"),
            "classification": review["classification"],
            "approval_record": approval,
            "execution_status": "NOT_EXECUTED",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "change_packet_schema": 1,
        }
        return commit

    def _validate_candidate(self, candidate: dict[str, Any]) -> None:
        required = {
            "candidate_id", "candidate_revision", "source_hash", "status",
            "content", "content_hash", "submitter", "proposed_operation",
        }
        missing = required - set(candidate)
        if missing:
            raise ReviewError(f"candidate contract missing fields: {sorted(missing)}")
        if candidate["status"] not in REVIEWABLE_STATUSES:
            raise ReviewError(f"candidate status is not reviewable: {candidate['status']}")
        if candidate["submitter"] == self._reviewer_identity:
            raise ReviewError("candidate submitter cannot review their own submission")
        if hashlib.sha256(candidate["content"].encode("utf-8")).hexdigest() != candidate["content_hash"]:
            raise ReviewError("candidate content hash mismatch")

    def _validate_approval(self, review: dict[str, Any], approval: dict[str, Any]) -> dict[str, Any]:
        required = {"approval_id", "review_id", "approver_identity", "authority", "decision", "issued_at"}
        if not isinstance(approval, dict) or required - set(approval):
            raise ApprovalInvalid("approval artifact is incomplete")
        if any(not isinstance(approval[field], str) or not approval[field].strip() for field in required):
            raise ApprovalInvalid("approval artifact fields must be non-empty strings")
        if approval["review_id"] != review["review_id"] or approval["decision"] != "APPROVE":
            raise ApprovalInvalid("approval does not authorize this review")
        if approval["authority"] not in APPROVER_AUTHORITIES:
            raise ApprovalInvalid("approval authority is not recognized")
        if approval["approver_identity"] == review["reviewer_identity"]:
            raise ApprovalInvalid("reviewer cannot approve their own review")
        if review.get("founder_approval_required") and approval["authority"] != "FOUNDER":
            raise FounderApprovalRequired(f"review {review['review_id']} requires FOUNDER authority")
        if self._approval_verifier is None or not self._approval_verifier(approval):
            raise ApprovalInvalid("approval artifact could not be verified")
        return dict(approval)

    def _load_candidate(self, candidate_id: str) -> dict[str, Any]:
        for candidate in self._load_all_candidates():
            if candidate.get("candidate_id") == candidate_id:
                return candidate
        raise CandidateNotFound(f"candidate not found in queue: {candidate_id}")

    def _load_all_candidates(self) -> list[dict[str, Any]]:
        if not self._queue_path.is_file():
            return []
        try:
            source_bytes = self._queue_path.read_bytes()
        except OSError as exc:
            raise ReviewError(f"candidate queue unreadable: {self._queue_path}") from exc
        if not source_bytes.strip():
            return []
        records: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(source_bytes.splitlines(), start=1):
            if not raw_line.strip():
                continue
            try:
                records.append(json.loads(raw_line))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReviewError(f"invalid JSON at queue line {line_number}") from exc
        return records

    def _classify_candidate(self, candidate: dict[str, Any]) -> str:
        proposed_knowledge_id = candidate.get("proposed_knowledge_id")
        proposed_operation = candidate.get("proposed_operation", "UNKNOWN")
        content_hash = candidate.get("content_hash")

        if not proposed_knowledge_id:
            if proposed_operation == "CREATE":
                return "NEW_KNOWLEDGE"
            return "INSUFFICIENT_EVIDENCE"

        try:
            current = self._repository.get(proposed_knowledge_id)
        except CanonicalKnowledgeNotFound:
            if proposed_operation in ("UPDATE", "SUPERSEDE", "RETIRE"):
                return "INSUFFICIENT_EVIDENCE"
            return "NEW_KNOWLEDGE"

        if proposed_operation == "RETIRE":
            return "RETIREMENT"

        if proposed_operation == "SUPERSEDE":
            return "SUPERSESSION"

        if proposed_operation == "UPDATE":
            base_revision = candidate.get("base_canonical_revision")
            if base_revision is not None and base_revision < current["revision"]:
                return "CONFLICT"
            if self._is_duplicate_content(candidate, current):
                return "DUPLICATE"
            if self._is_reaffirmation(candidate, current):
                return "REAFFIRMATION"
            return "UPDATE"

        return "INSUFFICIENT_EVIDENCE"

    def _is_duplicate_content(self, candidate: dict[str, Any], current: dict[str, Any]) -> bool:
        candidate_content = candidate.get("content", "").strip().lower()
        current_content = current.get("content", "").strip().lower()
        if not candidate_content or not current_content:
            return False
        return candidate_content == current_content or candidate_content in current_content

    def _is_reaffirmation(self, candidate: dict[str, Any], current: dict[str, Any]) -> bool:
        import re
        candidate_summary = candidate.get("content", "").strip().lower()
        current_summary = current.get("summary", "").strip().lower()
        current_content = current.get("content", "").strip().lower()
        if not candidate_summary:
            return False
        if candidate_summary == current_summary:
            return True
        candidate_words = set(re.findall(r'\w+', candidate_summary))
        current_words = set(re.findall(r'\w+', current_summary + " " + current_content))
        if not candidate_words:
            return False
        overlap = len(candidate_words & current_words) / len(candidate_words)
        return overlap > 0.8

    def _analyze_evidence(self, candidate: dict[str, Any], classification: str) -> dict[str, Any]:
        proposed_knowledge_id = candidate.get("proposed_knowledge_id")
        provenance_refs = candidate.get("evidence_ids", candidate.get("provenance_refs", []))
        claimed_evidence = set(provenance_refs)
        verified_evidence = claimed_evidence & self._verified_evidence_ids
        unverified_evidence = claimed_evidence - verified_evidence
        result: dict[str, Any] = {
            "supporting": sorted(verified_evidence),
            "contradicting": [],
            "unverified": sorted(unverified_evidence),
            "provenance_status": "VERIFIED" if claimed_evidence and not unverified_evidence else ("PARTIAL" if verified_evidence else "UNVERIFIED"),
            "confidence": 0.5,
            "rationale": "",
            "current_revision": None,
        }

        if not proposed_knowledge_id:
            result["rationale"] = "No knowledge_id reference; classification based on operation alone."
            if classification == "NEW_KNOWLEDGE":
                result["confidence"] = 0.6
            return result

        try:
            current = self._repository.get(proposed_knowledge_id)
        except CanonicalKnowledgeNotFound:
            result["rationale"] = f"knowledge_id {proposed_knowledge_id} not found in canonical store."
            result["confidence"] = 0.3
            return result

        result["current_revision"] = current["revision"]
        existing_evidence = set(current.get("evidence_ids", []))
        candidate_evidence = verified_evidence
        new_evidence = candidate_evidence - existing_evidence

        if new_evidence:
            result["supporting"] = list(new_evidence)
            result["provenance_status"] = "VERIFIED_EXTENDED"
            result["confidence"] = min(0.9, 0.5 + 0.1 * len(new_evidence))
        elif candidate_evidence:
            result["provenance_status"] = "VERIFIED_OVERLAP"
            result["confidence"] = 0.7
        else:
            result["provenance_status"] = "UNVERIFIED"
            result["confidence"] = 0.4

        if classification == "DUPLICATE":
            result["rationale"] = "Candidate content matches current canonical revision exactly."
            result["confidence"] = 0.95
        elif classification == "REAFFIRMATION":
            result["rationale"] = "Candidate substantially restates current canonical knowledge."
            result["confidence"] = 0.85
        elif classification == "CONFLICT":
            result["rationale"] = f"Candidate base revision is stale (base={candidate.get('base_canonical_revision')}, current={current['revision']})."
            result["contradicting"] = sorted(
                set(candidate.get("contradicting_evidence_ids", [])) & self._verified_evidence_ids
            )
            result["confidence"] = 0.6
        elif classification == "UPDATE":
            result["rationale"] = f"Candidate proposes update to revision {current['revision']} with new evidence."
        elif classification == "SUPERSESSION":
            result["rationale"] = f"Candidate proposes supersession of current revision {current['revision']}."
        elif classification == "RETIREMENT":
            result["rationale"] = f"Candidate proposes retirement of knowledge_id {proposed_knowledge_id}."

        return result

    def _requires_founder_approval(self, candidate: dict[str, Any], classification: str) -> bool:
        if classification in AUTO_CLEAR_CLASSIFICATIONS | {"INSUFFICIENT_EVIDENCE", "REJECTED"}:
            return False
        if classification in ("RETIREMENT", "CONFLICT"):
            return True
        proposed_knowledge_id = candidate.get("proposed_knowledge_id")
        governance_domain = str(candidate.get("governance_domain", "")).lower()
        identity = f"{proposed_knowledge_id or ''} {governance_domain}".lower()
        if any(domain in identity for domain in FOUNDER_REQUIRED_DOMAINS | {"derekos", "constitution"}):
            return True
        if classification == "SUPERSESSION":
            return True
        return False

    def _build_commit_proposal(self, candidate: dict[str, Any], classification: str, evidence_analysis: dict[str, Any]) -> dict[str, Any]:
        proposed_knowledge_id = candidate.get("proposed_knowledge_id")
        current_revision = evidence_analysis.get("current_revision")

        if classification in ("DUPLICATE", "REAFFIRMATION", "INSUFFICIENT_EVIDENCE", "REJECTED"):
            return {
                "action": "NO_COMMIT",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": current_revision,
                "rationale": f"Classification {classification} does not require canonical commit.",
            }

        if classification == "CONFLICT":
            return {
                "action": "DEFER",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": current_revision,
                "rationale": "Conflict requires a governed resolution before any canonical change.",
            }

        if not evidence_analysis.get("supporting"):
            return {
                "action": "EVIDENCE_REQUIRED",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": current_revision,
                "rationale": "No verified supporting evidence is attached to this canonical change.",
            }

        if classification == "NEW_KNOWLEDGE":
            return {
                "action": "CREATE",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": 1,
                "requires_knowledge_id_assignment": proposed_knowledge_id is None,
                "content": candidate.get("content", ""),
                "evidence_ids": evidence_analysis.get("supporting", []),
                "rationale": "New knowledge record proposed from candidate.",
            }

        if classification == "UPDATE":
            return {
                "action": "UPDATE",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": (current_revision or 0) + 1,
                "content": candidate.get("content", ""),
                "evidence_ids": evidence_analysis.get("supporting", []),
                "rationale": f"Update to revision {(current_revision or 0) + 1} proposed from candidate.",
            }

        if classification == "SUPERSESSION":
            return {
                "action": "SUPERSEDE",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": (current_revision or 0) + 1,
                "supersedes_revision": current_revision,
                "content": candidate.get("content", ""),
                "evidence_ids": evidence_analysis.get("supporting", []),
                "rationale": f"Supersedes revision {current_revision} with new revision {(current_revision or 0) + 1}.",
            }

        if classification == "RETIREMENT":
            return {
                "action": "RETIRE",
                "knowledge_id": proposed_knowledge_id,
                "proposed_revision": (current_revision or 0) + 1,
                "retires_revision": current_revision,
                "rationale": f"Retires knowledge_id {proposed_knowledge_id} at revision {current_revision}.",
            }

        return {
            "action": "NO_COMMIT",
            "knowledge_id": proposed_knowledge_id,
            "proposed_revision": current_revision,
            "rationale": "No commit proposal for this classification.",
        }

    def _build_conflict_packet(self, candidate: dict[str, Any], classification: str, evidence_analysis: dict[str, Any]) -> dict[str, Any]:
        proposed_knowledge_id = candidate.get("proposed_knowledge_id")
        current_revision = evidence_analysis.get("current_revision")
        try:
            current = self._repository.get(proposed_knowledge_id) if proposed_knowledge_id else None
        except CanonicalKnowledgeNotFound:
            current = None

        return {
            "current_state": {
                "knowledge_id": proposed_knowledge_id,
                "revision": current_revision,
                "title": current.get("title") if current else None,
                "content": current.get("content") if current else None,
                "evidence_ids": current.get("evidence_ids", []) if current else [],
            } if current else None,
            "proposed_state": {
                "content_summary": candidate.get("content_summary", ""),
                "base_revision": candidate.get("base_canonical_revision"),
                "proposed_operation": candidate.get("proposed_operation"),
            },
            "supporting_evidence": evidence_analysis.get("supporting", []),
            "contradicting_evidence": evidence_analysis.get("contradicting", []),
            "founder_decision_required": True,
        }

    def _load_review(self, review_id: str) -> dict[str, Any]:
        if not self._review_log_path.is_file():
            raise ReviewError(f"review not found: {review_id}")
        for review in self._read_review_log():
            if review.get("review_id") == review_id:
                return review
        raise ReviewError(f"review not found: {review_id}")

    def _read_review_log(self) -> list[dict[str, Any]]:
        if not self._review_log_path.is_file():
            return []
        try:
            source_bytes = self._review_log_path.read_bytes()
        except OSError as exc:
            raise ReviewError(f"review log unreadable: {self._review_log_path}") from exc
        if not source_bytes.strip():
            return []
        records: list[dict[str, Any]] = []
        for line_number, raw_line in enumerate(source_bytes.splitlines(), start=1):
            if not raw_line.strip():
                continue
            try:
                records.append(json.loads(raw_line))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ReviewError(f"invalid JSON at review log line {line_number}") from exc
        return records

    def _append_review_log(self, review: dict[str, Any]) -> None:
        self._review_log_path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(review, sort_keys=True) + "\n"
        with open(self._review_log_path, "a", encoding="utf-8") as output:
            output.write(line)
            output.flush()
            os.fsync(output.fileno())

    @staticmethod
    def _log_review(review: dict[str, Any]) -> None:
        LOGGER.info(
            "master_brain_review review_id=%s candidate_id=%s classification=%s confidence=%.2f founder_required=%s",
            review["review_id"],
            review["candidate_id"],
            review["classification"],
            review["confidence"],
            review["founder_approval_required"],
        )

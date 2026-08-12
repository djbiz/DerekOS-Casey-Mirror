# MASTER_BRAIN_REVIEW_COMMIT_WORKFLOW_V0.1

**Status:** Slice 4 implemented and verified

**Depends on:** Knowledge Contract; canonical Slices 1–3 (`edb67da`, `9a47df8`, `3cf9fb4`)

## Purpose

Analyze governed candidate revisions, compare them with current canon, preserve conflicts and provenance, and produce non-executing canonical change packets after independently verifiable approval.

Slice 4 does not write `canonical_records.jsonl`. Analysis is advisory; approval is external; execution remains a separate future authority.

## Separation of duties

```text
Candidate submitter
  -> reviewer (cannot be submitter)
  -> evidence verification
  -> review record / recommendation
  -> external approval artifact
  -> approval verifier
  -> canonical change packet (NOT_EXECUTED)
  -> future canonical commit service (not implemented)
```

No boolean such as `founder_approved=True` is authority. A change packet requires an approval artifact containing approval ID, review ID, approver identity, authority, decision, and issue time, plus a configured verifier that accepts it. With no verifier, production change-packet generation fails closed.

## Reviewable candidate contract

Candidates must come from the governed Slice 3 shape and include immutable candidate ID/revision, source hash, complete content and matching content hash, submitter identity, operation, and a reviewable intake status (`SUBMITTED`, `REVIEW_READY`, or `CONFLICT_OPEN`). Malformed records and self-review fail visibly.

## Evidence

Candidate evidence references are claims. Only IDs supplied by the configured evidence-verification boundary count as supporting evidence. Unverified references are reported separately and cannot support `CREATE`, `UPDATE`, `SUPERSEDE`, or `RETIRE` packets.

If no verified evidence supports a proposed canonical change, the review action is `EVIDENCE_REQUIRED`, and approval cannot convert it into a change packet.

## Classifications

`DUPLICATE`, `REAFFIRMATION`, `NEW_KNOWLEDGE`, `UPDATE`, `SUPERSESSION`, `RETIREMENT`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`, and `REJECTED`.

- Duplicate/reaffirmation/insufficient/rejected -> `NO_COMMIT`.
- Conflict -> `DEFER` with a conflict packet.
- Evidence-free change -> `EVIDENCE_REQUIRED`.
- Verified new/update/supersession/retirement -> a proposed action, still requiring approval.

Keyword overlap and confidence are advisory heuristics only. They never supply authority or verified evidence.

## Approval rules

Recognized authority classes are `FOUNDER`, `ARCHITECTURE_BOARD`, and `KNOWLEDGE_CURATOR`. Founder authority is mandatory for conflict, retirement, supersession, constitutional/governance/master-plan/major-strategy, and DerekOS-sensitive changes. The reviewer cannot approve their own review.

The approval verifier is injected by the caller. `from_environment()` intentionally configures none, so production approval remains unavailable until a canonical identity/approval verifier is wired.

## Output

`propose_canonical_commit()` retains its name for API continuity but returns a `change_packet_id` with `execution_status: NOT_EXECUTED`. It never changes canonical bytes or status.

## Verification

```powershell
python -m unittest 14_TESTS_AUDITS.test_master_brain_review_workflow -v
```

Result: **19 passed, 0 failed**.

Coverage includes duplicate/reaffirmation/update/supersession/retirement/conflict/new/insufficient classifications, malformed-candidate denial, canonical non-mutation, structured founder authority, history-preserving revisions, append-only review logging, batch review, self-review denial, boolean/incomplete approval denial, unverified-evidence blocking, and no-verifier fail-closed behavior.

## Explicit exclusions

- No canonical store mutation or canonical commit executor.
- No self-approval or boolean approval.
- No automatic evidence trust.
- No background review, watcher, or sync.
- No VOX operational write or index/mount change.
- No real canonical records produced by this slice.

## Build Report

### Changes made

Consolidated the existing Slice 4 draft into the canonical bridge and corrected candidate validation, self-review, evidence verification, approval-artifact verification, founder-sensitive classification, and non-executing change-packet behavior. Added 19 fixture-based acceptance tests.

### Validation evidence

The focused suite and all Slice 1–3 regressions pass. Tests use temporary canonical, candidate, review-log, and approval fixtures only. Production canonical and Obsidian stores remain unchanged.

### Remaining risks

- No production evidence resolver or approval verifier is wired; production change packets remain disabled.
- Heuristic similarity requires human review and must not be represented as semantic proof.
- No canonical commit executor exists, deliberately.

### Recommended next step

Stop bridge expansion. Begin a governed reconstruction pilot for the Conglomerate / Corporate Takeover branch: evidence selection first, then candidate canonical records, human review, and only afterward an explicitly authorized canonical commit mechanism.

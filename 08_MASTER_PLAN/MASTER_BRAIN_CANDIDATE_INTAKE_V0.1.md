# MASTER_BRAIN_CANDIDATE_INTAKE_V0.1

**Status:** Slice 3 implemented and verified

**Depends on:** Knowledge Contract, Slice 1 retrieval, canonical Slice 2 publisher (`9a47df8`)

## Purpose

Provide an explicit, one-way intake from Obsidian `MasterBrain/Candidates/` to an append-only Master Brain candidate queue. Intake never mutates evidence, canonical records, published projections, or VOX state.

## Governance boundary

- A candidate note is untrusted input.
- Frontmatter cannot approve, reject, or promote itself.
- `submitter` comes from configured caller identity; a frontmatter value is retained only as `claimed_submitter`.
- Intake statuses are only `SUBMITTED`, `CONFLICT_OPEN`, and `REVIEW_READY`.
- `ACCEPTED` and `REJECTED` are review dispositions, never intake states.
- No filesystem watcher, reverse sync, or automatic review exists.

## Candidate identity and revisions

`candidate_id` is stable for a vault-relative source path. Unchanged content at that path is idempotent. Changed content creates an immutable next `candidate_revision`. Identical content at a different path is a distinct submission and is not collapsed.

Each queued record preserves:

- candidate ID and revision;
- `source_system: obsidian`;
- vault ID, relative path, source SHA-256;
- configured submitter and any untrusted claimed submitter;
- proposed operation/knowledge ID/base revision;
- complete submitted body, summary, and SHA-256;
- claimed evidence/provenance references;
- submitted timestamp and intake status.

## Initial status

| Condition | Status |
|---|---|
| No canonical ID, repository, or known canonical record | `SUBMITTED` |
| Base revision is older than current canon | `CONFLICT_OPEN` |
| Referenced base revision matches current canon | `REVIEW_READY` |

Malformed optional metadata normalizes to `UNKNOWN`/`null`; malformed paths, symlinks, queues, and custody boundaries fail visibly.

## Storage and paths

- Source subtree must be exactly `MasterBrain/Candidates/` under an existing vault root.
- `MasterBrain/Published/` cannot be ingested as a candidate.
- Queue defaults to `12_CONFLICTS/candidate_queue.jsonl` and is append-only.
- Candidate source files are never modified by intake.

## Verification

```powershell
python -m unittest 14_TESTS_AUDITS.test_master_brain_candidate_intake -v
```

Result: **21 passed, 0 failed**.

Coverage includes path confinement, symlink/published rejection, stable IDs and revisions, idempotency, distinct-path preservation, stale conflict detection, complete content custody, provenance references, source/canonical non-mutation, logging, batch intake, malformed metadata, and denial of self-declared acceptance.

## Explicit exclusions

- No canonical mutation.
- No review decision or approval.
- No conflict resolution.
- No watcher/background scan.
- No VOX write, index rebuild, Docker change, or bidirectional synchronization.

## Build Report

### Changes made

Added the existing `CandidateIntake` draft to the canonical bridge after correcting identity, revision, status, source-custody, and self-approval defects. Added 21 fixture-based tests.

### Validation evidence

All tests use temporary vault, queue, and canonical fixtures. No real candidate directory or production queue was created.

### Remaining risks

Production candidate intake remains inactive. Provenance references are claims until Slice 4 verifies them. Concurrent queue writers will eventually require an explicit locking/transaction strategy before service deployment.

### Recommended next step

Review and harden Slice 4 so it consumes these governed records, separates analysis from approval, requires verifiable approval artifacts, and produces proposals without mutating canon.

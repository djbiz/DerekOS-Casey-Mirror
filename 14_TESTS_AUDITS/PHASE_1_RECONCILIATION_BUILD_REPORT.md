# Phase 1 Reconciliation Build Report

## Changes made

- Confirmed `D:\Projects\VOX\DerekOS_Master_Brain` as the canonical workspace.
- Preserved its main/alternate branch model, current-node ordering, content extraction, Build Spec v2, and Phase 2 pilot.
- Added stable source-record IDs, source-file SHA-256, mapping-node identity, parent/child topology, ingest versioning, atomic output replacement, and an idempotent checkpoint.
- Added the canonical per-file source manifest and versioned message schema.
- Added a bounded reconciliation verifier.
- Did not copy the Downloads normalized corpus or replace the canonical specification.

## Source custody incident and recovery

During the first reconciliation run, another process removed or replaced primary raw files while the parser was reading them. The run failed honestly at `conversations-013.json`; the existing canonical `messages.jsonl` was preserved and only the partial `.tmp` output was removed.

The 35 primary files were restored from the already-verified identical read-only corpus copy. A second concurrent file operation briefly left one mismatch. Reconciliation stopped, then resumed only after the directory stabilized. Final custody verification proves 35/35 hashes match and every primary source is read-only.

## Validation evidence

- Source files: 35/35.
- Raw hash parity: PASS.
- Raw read-only enforcement: PASS.
- Conversations: 3,476.
- Mapping nodes: 72,237.
- Normalized messages: 68,761.
- Structural roots without messages: 3,476.
- Node reconciliation: PASS.
- Unique stable source-record IDs: 68,761.
- Duplicate conversation IDs: 0.
- Anomalous current nodes: 0.
- Parent/child graph links: PASS.
- Versioned schema sample: 168/168 PASS.
- Exact contract-key check: 68,761/68,761 PASS.
- Existing Phase 2 pilot citations remain resolvable: 10/10 PASS.
- Repeated normalized output SHA-256: `de5fd49c7775a1eee9891a996b2c7e01d6668517d1a7aeb8e7b318e3ebacd9ea`.
- Deterministic rerun: PASS.

## Repository baseline correction

- Initialized a standalone Git repository at the canonical D: workspace; it is not nested in `vox_v4`.
- Added Git attributes and exclusions so immutable private raw exports and reproducible large generated corpora cannot enter Git history.
- Marked the Downloads workspace explicitly noncanonical without deleting it.
- Concurrent root-level ingestion, schemas, provenance tooling, and source indexes were preserved and included in the initial baseline rather than silently overwritten.

## Remaining risks

- The Phase 2 pilot's earlier report documents several excerpts normalized across whitespace/Markdown or spanning interpretation boundaries. This reconciliation proves citation survival, not a new independent semantic audit.
- The Downloads workspace still exists and must remain explicitly noncanonical or be archived after user approval.

## Recommended next step

Run Audit Bot read-only against the canonical D: workspace. It should verify source custody, deterministic ingestion, random main/alternate branch samples, and all ten pilot attribution/evidence classifications before Phase 2 scales beyond the existing pilot.

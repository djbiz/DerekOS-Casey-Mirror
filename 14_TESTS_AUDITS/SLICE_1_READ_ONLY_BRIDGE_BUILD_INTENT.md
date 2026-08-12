# Slice 1 Read-Only Master Brain Retrieval Bridge — Build Intent

**Date:** 2026-08-12
**Status:** Authorized for bounded implementation
**Baseline:** `b05bfed`

## What was inspected

- The accepted Knowledge Contract and Slice 0 path reconciliation.
- The empty `10_CANONICAL_KNOWLEDGE/` surface.
- Existing evidence, thought, schema, audit, and test conventions.
- Current working-tree changes, which belong to concurrent ingestion/provenance work.

## Current architecture state

Master Brain has immutable evidence and normalized ingestion outputs, but no populated accepted canonical-record store and no read interface. The absence of canonical records is a valid unavailable state and must not trigger fallback to Obsidian, BM25, Chroma, PostgreSQL sync state, or the empty Docker vault mount.

## Proposed changes

- Add a small standard-library Python package that reads a configured canonical JSONL store without writing to it.
- Validate canonical records and revision invariants at the boundary.
- Support exact ID/current revision, historical revision, and direct canonical-text query search.
- Return explicit authority, canonical status, provenance references, and store metadata.
- Fail visibly when the canonical store is missing, empty, malformed, or inconsistent.
- Add temporary-fixture tests proving retrieval behavior and filesystem non-mutation.
- Document the interface and its limits in `MASTER_BRAIN_READ_ONLY_BRIDGE_V0.1.md`.

## Files affected

- `master_brain_bridge/__init__.py`
- `master_brain_bridge/repository.py`
- `14_TESTS_AUDITS/test_master_brain_read_only_bridge.py`
- `14_TESTS_AUDITS/SLICE_1_READ_ONLY_BRIDGE_BUILD_INTENT.md`
- `08_MASTER_PLAN/MASTER_BRAIN_READ_ONLY_BRIDGE_V0.1.md`

## Ownership domain

Master Brain canonical retrieval boundary. This slice does not transfer ownership to VOX, DerekOS, Obsidian, or an index.

## Risks

- A future caller might mistake search relevance for canonical authority.
- Malformed or duplicate revisions could create ambiguous current state.
- Logging a filesystem path could disclose host layout if propagated externally.
- “Semantic” may be overstated when the bounded implementation performs direct canonical-text query matching without embeddings.

## Verification plan

- Use isolated temporary canonical JSONL fixtures.
- Prove exact, current, superseded, provenance, query, authority metadata, and unavailable-store behavior.
- Snapshot configured canonical, Obsidian, and VOX-state paths before and after retrieval.
- Prove no Docker vault dependency and no derived-index authority.
- Run the focused tests repeatedly and run existing reconciliation validation.
- Stage and commit only Slice 1 files.

## Final change question

**Does this move VOX closer to becoming the AI Workforce Operating System?** Yes. It adds a single fail-honest read boundary through which VOX and DerekOS can consume governed knowledge without duplicating or mutating authority.

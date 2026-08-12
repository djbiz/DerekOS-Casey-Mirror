# Phase 1 Reconciliation Build Intent

## Inspected

- Canonical D: build specification, ingestion implementation, outputs, Phase 2 pilot, and audit utilities.
- Downloads ingestion implementation, schemas, manifest, topology audit, and build evidence.
- Raw corpus hashes in both workspaces.

## Current architecture state

`D:\Projects\VOX\DerekOS_Master_Brain` is canonical and already has the stronger semantic ingestion model: all mapping messages, explicit main/alternate branch classification, current-node ordering, and extraction for all four observed content types. The Downloads workspace is a competing implementation and must not become a second brain.

Verified gaps in the canonical Phase 1 pipeline are stable message IDs, per-source hashes, atomic output replacement, deterministic output proof, a versioned schema, and a canonical source manifest.

## Proposed changes

- Add stable `source_record_id`, `source_sha256`, `node_id`, and graph parent/children fields without removing existing fields.
- Make output ordering deterministic and writes atomic/restartable.
- Add an immutable versioned message schema and source-manifest schema.
- Generate a canonical source manifest and expanded fail-honest ingest report.
- Add focused Phase 1 validation proving counts, branches, hashes, stable IDs, and raw immutability.
- Record the Downloads workspace as noncanonical; do not copy its normalized corpus into D:.

## Files affected

- `01_INGEST/ingest.py`
- `01_INGEST/README.md`
- `01_INGEST/schemas/*`
- Generated canonical outputs in `01_INGEST/`
- `13_SOURCE_INDEX/source_manifest.json`
- Phase 1 reconciliation evidence in `14_TESTS_AUDITS/`

## Ownership domain

- Codex: parsing, normalized data, manifests, deterministic verification.
- OpenCode contract improvements are incorporated only where compatible with the canonical D: specification.

## Risks

- Existing Phase 2 pilot cites `message_id`; those values and all existing message fields must remain unchanged.
- Full output regeneration is large and must not leave partial files.
- Raw corpus must remain byte-identical and read-only.

## Verification plan

- Re-run ingestion twice and compare output hashes.
- Validate all records against structural invariants and a bounded formal-schema sample.
- Reconcile 35 files, 3,476 conversations, 72,237 nodes, 68,761 messages, and 3,476 structural roots.
- Verify every main path, parent/child link, stable ID, and raw hash.
- Revalidate all 10 Phase 2 pilot source citations against regenerated `messages.jsonl`.

Final change question: **Does this move DerekOS closer to a trustworthy AI memory operating system? Yes—by establishing one reproducible, provenance-bearing ingest baseline without duplicating the brain.**

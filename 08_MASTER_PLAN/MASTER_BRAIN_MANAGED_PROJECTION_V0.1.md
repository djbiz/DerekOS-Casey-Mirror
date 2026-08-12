# MASTER_BRAIN_MANAGED_PROJECTION_V0.1

**Status:** Slice 2 implemented and verified

**Depends on:**

- Knowledge Contract: `71b705a8093f91c84f8b2e40397919ce6e809afe`
- Path reconciliation: `b05bfed`
- Read-only bridge: `edb67da`

## Purpose

Provide one bounded, one-way, revision-aware publisher that renders explicitly publishable, accepted, current Master Brain canonical records as human-readable Obsidian notes inside a dedicated managed projection subtree.

This slice proves the publishing boundary. It does not implement candidate intake, bidirectional synchronization, file watchers, or VOX runtime call-site wiring.

## Interface

```python
from master_brain_bridge import ReadOnlyCanonicalRepository, ManagedProjectionPublisher

repository = ReadOnlyCanonicalRepository.from_environment()
publisher = ManagedProjectionPublisher.from_environment(repository)

receipt = publisher.publish("MBK-DEREKOS-DECISION-01K...")
receipts = publisher.publish_all_current()
```

The publisher is invoked only when a caller explicitly targets Master Brain canonical publishing. No existing VOX retrieval route is replaced or silently intercepted.

## Projection contract

### Managed subtree

All published notes live under `MasterBrain/Published/` within the canonical Obsidian vault. The publisher validates that this subtree is inside the vault root and refuses to write outside it.

### Filename

Filenames are derived from `knowledge_id` only, not from the title. This ensures stable paths across title changes and revision updates:

```
MasterBrain/Published/MBK-DEREKOS-DECISION-01KTEST0001.md
```

### Frontmatter

Every managed note includes explicit ownership markers:

```yaml
---
master_brain_managed: true
knowledge_id: MBK-DEREKOS-DECISION-01KTEST0001
canonical_revision: 2
canonical_status: current
approval_status: accepted
projection_policy: publish
projection_schema: 1
source_authority: MASTER_BRAIN_CANONICAL_STORE
canonical_hash: 7a00b5706e1766d01f1a39cb78e36f9608d6ada7ffca3354adc5f0e315b5949e
projected_body_sha256: "..."
---
```

### Body

The note body includes:

- Title as H1
- Summary as italic lead
- Content section
- Provenance section with knowledge_id, revision, status, and evidence_ids
- Explicit non-authoritative marker: "This note is a managed projection of canonical Master Brain knowledge. It is not the authoritative source. Edits create candidates for evaluation."

### Canonical hash

The `canonical_hash` is a SHA-256 of the canonical record's identity fields (knowledge_id, revision, canonical_status, title, summary, content, evidence_ids). It is used for idempotency: if the hash has not changed, the note is not rewritten.

## Publishing behavior

### Idempotent

If the canonical record revision has not changed (by canonical_hash), the note is not rewritten. The file modification time remains unchanged.

### Revision-aware

The publisher may publish only a record for which all three gates are true:

- `canonical_status: CURRENT`
- `approval_status: ACCEPTED`
- `projection_policy: PUBLISH`

Historical and superseded records remain retrievable through Slice 1 but cannot be projected as the current warm note. Updates must increase the projected revision monotonically.

### Deterministic

The same canonical record always produces the same note content. Runtime timestamps are excluded from the projection body, and the filename derives from knowledge_id only.

### Reversible

Deleting a managed note does not affect the canonical store. The publisher can republish it only while the canonical record remains eligible.

### Fail-visible

The publisher raises explicit exceptions for:

- `PathCollisionError`: A human-authored note exists at the target projection path.
- `UnauthorizedWriteError`: The managed subtree escapes the vault root, or the note path escapes the managed subtree.
- `CanonicalRecordInvalid`: The canonical record violates the projection contract.
- `ProjectionError`: Base exception for projection failures.

## Read-only guarantees

- The canonical store is opened only through `ReadOnlyCanonicalRepository`, which reads via `Path.read_bytes()`.
- The publisher writes only to `MasterBrain/Published/` within the configured vault root.
- The publisher validates that the managed subtree is inside the vault root before writing.
- The publisher validates that each note path is inside the managed subtree before writing.
- Notes are written atomically via a unique same-directory temporary file, flush/fsync, and replacement.
- The publisher never writes outside the managed subtree, even if the projection_subtree parameter contains path traversal sequences.
- A managed-body hash detects human or out-of-band changes and blocks overwrite.
- Safe knowledge-ID validation rejects separator and traversal payloads rather than sanitizing them into paths.
- Instantiating the publisher creates no directory. The subtree is created only after an eligible record is resolved.

## Acceptance evidence

Focused command:

```powershell
python -m unittest 14_TESTS_AUDITS.test_master_brain_managed_projection -v
```

Result: see committed Build Report; tests run exclusively against temporary fixtures.

Coverage proves:

1. first publish creates managed note with correct frontmatter;
2. no-op republish when revision unchanged (file not rewritten);
3. monotonic accepted-current revision update rewrites the note;
4. superseded records are denied and cannot replace current projections;
5. malformed canonical input fails visible;
6. path collision with human-authored note detected;
7. unauthorized write outside managed subtree prevented;
8. provenance metadata preserved in note;
9. no writes outside MasterBrain/Published/;
10. publish_all_current publishes only CURRENT records;
11. projection is logged;
12. managed note has explicit non-authoritative marker;
13. unapproved records create no directory or note;
14. human edits to managed content block overwrite.

Slice 1 regression: **11 passed, 0 failed**.

## Explicit exclusions

- No Obsidian-to-Master-Brain submission.
- No candidate intake or file watchers.
- No VOX operational-store mutation.
- No BM25 or Chroma rebuild.
- No PostgreSQL sync-state change.
- No Docker mount correction.
- No canonical promotion or data migration.
- No VOX runtime call-site wiring.
- No bidirectional synchronization.

## Build Report

### Changes made

- Added `master_brain_bridge.publisher.ManagedProjectionPublisher`.
- Added `master_brain_bridge.repository.ReadOnlyCanonicalRepository.knowledge_ids` property.
- Added path traversal protection in `_ensure_managed_subtree`.
- Added atomic file writing via unique temporary file replacement.
- Added frontmatter parsing with quote stripping.
- Added canonical hash computation for idempotency.
- Corrected the concurrent draft so superseded/unapproved records cannot publish and managed-body edits cannot be overwritten.
- Added fifteen focused acceptance tests.
- Added this interface and evidence record.

### Why needed

VOX and DerekOS previously had no governed interface for publishing accepted Master Brain canonical knowledge as human-readable Obsidian notes. This slice proves the publishing boundary without enabling bidirectional synchronization or candidate intake.

### Tests run

- Slice 2 focused acceptance suite: 15 passed.
- Slice 1 regression suite: 11 passed, 0 failed.
- Python compilation: passed.

### Validation evidence

Tests use a temporary canonical store with current and superseded revisions, and a temporary vault root. The publisher creates managed notes in `MasterBrain/Published/` and validates path containment, collision detection, and idempotency.

### Remaining risks

- The production canonical JSONL store is not populated, so live canonical publishing remains honestly unavailable.
- VOX/DerekOS call-site wiring is not introduced in this slice; callers can explicitly invoke the publisher, but existing retrieval behavior remains untouched.
- The publisher does not implement candidate intake; human edits to managed notes are not automatically submitted to Master Brain.
- The publisher detects out-of-band edits and stops, but it does not create a candidate or conflict record; that remains a future slice.
- Production publication remains disabled in effect because `canonical_records.jsonl` is absent. The publisher was not invoked against the real vault.

### Recommended next step

Architecture review should accept or amend this interface. Production publication still requires at least one real accepted canonical record. Only after acceptance should Slice 3 consider candidate intake and review/conflict workflow.

## Final change question

**Does this move VOX closer to becoming the AI Workforce Operating System?** Yes. VOX and DerekOS now have a governed publish boundary that renders canonical knowledge as human-readable notes without Obsidian becoming the source of truth.

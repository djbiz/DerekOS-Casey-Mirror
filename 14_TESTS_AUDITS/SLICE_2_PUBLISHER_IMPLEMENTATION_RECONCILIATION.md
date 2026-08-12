# Slice 2 Publisher Implementation Reconciliation

**Date:** 2026-08-12
**Canonical baseline:** `9a47df8`
**Verdict:** ONE IMPLEMENTATION; CODEX BASELINE REMAINS CANONICAL

## Scope inspected

- `master_brain_bridge/publisher.py`
- `master_brain_bridge/__init__.py`
- `master_brain_bridge/repository.py`
- `14_TESTS_AUDITS/test_master_brain_managed_projection.py`
- `08_MASTER_PLAN/MASTER_BRAIN_MANAGED_PROJECTION_V0.1.md`
- `08_MASTER_PLAN/QODERWAKE_BRIDGE_RECONCILIATION_V0.1.md`
- Repository-wide publisher/class/path searches in the Master Brain and VOX workspaces

## Implementation identity finding

No second publisher file, package, service, class, or runtime route exists. The earlier QoderWake Slice 2 work appeared as an uncommitted draft in the same files later consolidated by Codex. Commit `9a47df8` contains the corrected and governed form of that draft.

Therefore, this is not a merge between two implementations. It is a disposition of behaviors within one implementation lineage.

## Duplicate files, classes, and functions

| Surface | QoderWake draft | Canonical `9a47df8` | Disposition |
|---|---|---|---|
| Publisher module | `master_brain_bridge/publisher.py` | Same path | Consolidated; one file remains |
| Publisher class | `ManagedProjectionPublisher` | Same class | Consolidated; one class remains |
| Package export | `master_brain_bridge.__init__` | Same export | Consolidated |
| Canonical ID enumeration | `ReadOnlyCanonicalRepository.knowledge_ids` | Same property | Retained |
| Acceptance suite | `test_master_brain_managed_projection.py` | Same suite | Expanded and corrected |
| Separate service/container | Proposed in older QoderWake architecture | None | Retired; no duplicate created |

## Behavior retained from the QoderWake draft

- One-way Master Brain Canonical → Obsidian publication.
- Stable filenames derived from `knowledge_id`.
- `MasterBrain/Published/` containment.
- Human-note collision detection.
- Canonical content hashing and idempotent no-op behavior.
- Provenance rendered into the note.
- Atomic same-directory replacement.
- `publish_all_current()` convenience operation.
- Projection receipts and structured process logging.
- Explicit note text stating that Obsidian is not authoritative.

These were useful and remain in the canonical implementation.

## Behavior present only in the governed Codex baseline

- Publication requires all three gates: `CURRENT + ACCEPTED + PUBLISH`.
- Canonical authority must be `MASTER_BRAIN_CANONICAL_STORE`.
- Superseded records cannot publish or downgrade a current projection.
- Unapproved records cannot create the managed subtree.
- Revisions must increase monotonically.
- Managed-body hashing detects human/out-of-band edits before overwrite.
- Knowledge IDs are rejected unless path-safe; separators/traversal are not sanitized into filenames.
- The write subtree must be exactly `MasterBrain/Published/`.
- The vault root must already exist.
- Unique temporary files, flush/fsync, and atomic replacement reduce concurrent-write risk.
- Production remains inactive while the canonical store is absent.

## Behavior retired from the QoderWake draft

- Publishing an explicitly requested superseded revision.
- Allowing a superseded record to replace a newer current projection.
- Publishing merely because a record exists in the canonical JSONL file.
- Treating a stored canonical hash alone as proof that the managed body was not edited.
- Runtime `published_at` values that made otherwise identical projections nondeterministic.
- Sanitizing path separators instead of rejecting unsafe IDs.
- A separate FastAPI publisher service/container.

## Test reconciliation

The original draft’s useful tests were not discarded. They evolved into the canonical 15-test suite.

| Coverage | Status |
|---|---|
| First publication/frontmatter | Retained |
| Idempotent republish/no mtime change | Retained |
| Monotonic revision upgrade | Strengthened |
| Superseded publication | Inverted from allow to mandatory deny |
| Human-authored collision | Retained |
| Path escape | Strengthened to constructor-time exact-subtree denial |
| Provenance metadata | Retained |
| No writes outside managed subtree | Retained |
| Publish all eligible current records | Strengthened with approval/policy gates |
| Structured logging | Retained |
| Non-authoritative marker | Retained |
| Unapproved publication | Added denial test |
| Modified managed body | Added denial test |
| Unsafe knowledge ID | Added denial test |

Latest accepted evidence: Slice 2 **15 passed**, Slice 1 regression **11 passed**, and full mixed-ingest reconciliation **PASS**.

## Conflicting semantics and decision

The only material conflict was whether any historical canonical revision could be projected. The canonical Knowledge Contract defines the managed note as the current human-readable projection, so the governed rule wins:

```text
CURRENT + ACCEPTED + PUBLISH
```

History remains retrievable through Slice 1. It does not masquerade as the current Obsidian projection.

## Retirement and consolidation disposition

- Keep `master_brain_bridge/publisher.py` from `9a47df8` as the only authoritative publisher.
- Keep the canonical 15-test suite.
- Keep `MASTER_BRAIN_MANAGED_PROJECTION_V0.1.md` as the implementation contract.
- Retain `QODERWAKE_BRIDGE_RECONCILIATION_V0.1.md` only as historical architecture-review evidence if committed by its owner; it is not an implementation contract.
- Do not create a QoderWake publisher service, alternate module, alternate managed subtree, or competing test suite.

## Exit criterion

Met. Repository search found one publisher implementation, one publisher class, one canonical test suite, and no competing runtime surface. `9a47df8` is the authoritative Slice 2 implementation baseline.

## Next workflow

Review the existing uncommitted Slice 3/4 candidate and review-workflow drafts against this canonical bridge before committing them. Slice 4 must consume governed candidate records and produce auditable proposals; it must not mutate canonical records or allow approval to be represented by an unauthenticated boolean.

# MASTER_BRAIN_READ_ONLY_BRIDGE_V0.1

**Status:** Slice 1 implemented and verified

**Depends on:**

- Knowledge Contract: `71b705a8093f91c84f8b2e40397919ce6e809afe`
- Path reconciliation: `b05bfed`

## Purpose

Provide one bounded, fail-honest interface through which VOX or DerekOS can explicitly retrieve accepted Master Brain canonical knowledge without mutating Master Brain, Obsidian, VOX operational state, or a derived index.

This slice proves the retrieval boundary. It does not claim that canonical promotion or the canonical-record population workflow is complete. Because `10_CANONICAL_KNOWLEDGE/canonical_records.jsonl` is not yet populated, the default production configuration currently fails visibly with `CanonicalStoreUnavailable` rather than returning evidence, warm notes, or search-index content as canon.

## Interface

```python
from master_brain_bridge import ReadOnlyCanonicalRepository

repository = ReadOnlyCanonicalRepository.from_environment()

current = repository.get("MBK-DEREKOS-DECISION-01K...")
historical = repository.get("MBK-DEREKOS-DECISION-01K...", revision=2)
results = repository.search("tenant ownership")
history_results = repository.search("earlier ownership", include_history=True)
```

The interface is invoked only when a caller explicitly targets Master Brain canonical knowledge. No existing VOX retrieval route is replaced or silently intercepted.

## Canonical source configuration

The repository reads exactly one JSONL source:

1. `MASTER_BRAIN_CANONICAL_STORE_PATH`, when explicitly configured; otherwise
2. `10_CANONICAL_KNOWLEDGE/canonical_records.jsonl` relative to this repository.

There is no fallback path. In particular, the bridge does not inspect:

- `OBSIDIAN_VAULT_PATH`;
- the current empty Docker `/vault` backing directory;
- BM25;
- Chroma;
- PostgreSQL `knowledge_sync_state`;
- VOX operational tables;
- raw conversation evidence as if it were canonical knowledge.

## Minimum canonical record

```json
{
  "knowledge_id": "MBK-DEREKOS-DECISION-01K...",
  "revision": 3,
  "canonical_status": "CURRENT",
  "title": "Three-temperature knowledge ownership",
  "summary": "Master Brain owns canon; Obsidian is warm; VOX is hot.",
  "content": "Accepted canonical interpretation.",
  "evidence_ids": ["source-record-id", "board-decision-id"]
}
```

Accepted statuses are `CANDIDATE`, `CURRENT`, `SUPERSEDED`, `REJECTED`, `CONFLICT`, and `RETIRED`. A store with duplicate `(knowledge_id, revision)` records or multiple `CURRENT` revisions for one ID fails closed.

## Response authority contract

Every returned record includes:

```json
{
  "knowledge_id": "...",
  "revision": 3,
  "canonical_status": "CURRENT",
  "evidence_ids": ["..."],
  "source_authority": "MASTER_BRAIN_CANONICAL_STORE",
  "authority_class": "AUTHORITATIVE",
  "source_temperature": "COLD_DEEP",
  "provenance": {
    "evidence_ids": ["..."]
  },
  "retrieval_authority": {
    "store_id": "master-brain-canonical-v0.1",
    "store_sha256": "...",
    "retrieved_from": "MASTER_BRAIN_CANONICAL_STORE",
    "indexed_from": null,
    "retrieval_mode": "current_revision"
  }
}
```

Retrieval events use the process logger and identify operation, authority, store ID, knowledge ID, revision, and canonical status. The bridge does not create a log file or write an audit database.

## Retrieval behavior

### Exact ID

`get(knowledge_id)` returns the one `CURRENT` revision. If no current revision exists, it fails rather than selecting the newest timestamp or revision implicitly.

### Historical revision

`get(knowledge_id, revision=n)` returns that exact revision with its actual status, including `SUPERSEDED`. History is never relabeled as current.

### Query search

`search(query)` performs bounded direct text matching over canonical `title`, `summary`, and `content`. It returns only `CURRENT` records by default. `include_history=True` is explicit.

This v0.1 mode is reported as `direct_canonical_text`. It is not described as vector-semantic retrieval and creates no new index. A future semantic locator may be added behind the interface, but the returned authority must still be resolved from the canonical store.

## Failure behavior

| Condition | Result |
|---|---|
| Store missing, unreadable, or empty | `CanonicalStoreUnavailable` |
| Invalid JSON or record contract | `CanonicalStoreInvalid` |
| Duplicate revision or ambiguous current revision | `CanonicalStoreInvalid` |
| Unknown ID/revision | `CanonicalKnowledgeNotFound` |
| Invalid query/limit/revision | `ValueError` |
| Empty/wrong Docker vault | No effect; never consulted |
| Derived index available but canonical store unavailable | Canonical retrieval fails; no fallback |

## Read-only guarantees

- The configured source is opened only through `Path.read_bytes()`.
- Source bytes are hashed with SHA-256 and then parsed into an in-memory snapshot.
- Public results are deep copies and cannot mutate the repository snapshot.
- No method creates, updates, deletes, renames, publishes, or synchronizes a file.
- No method imports an Obsidian or VOX persistence adapter.
- Tests snapshot canonical fixture, Obsidian sentinel, and VOX-state sentinel bytes before and after retrieval.

## Acceptance evidence

Focused command:

```powershell
python -m unittest 14_TESTS_AUDITS.test_master_brain_read_only_bridge -v
```

Result: **11 passed, 0 failed**.

Coverage proves:

1. exact knowledge-ID retrieval;
2. current-revision resolution;
3. canonical versus superseded distinction;
4. evidence/provenance preservation;
5. no Obsidian writes;
6. no VOX-state writes;
7. no derived index represented as authority;
8. visible missing/empty canonical-store failure;
9. authority/store metadata and retrieval logging;
10. no dependency on the wrong empty Docker vault mount;
11. ambiguous current revisions fail closed.

## Explicit exclusions

- No Obsidian publishing or managed-directory creation.
- No Obsidian-to-Master-Brain submission.
- No VOX operational-store mutation.
- No BM25 or Chroma rebuild.
- No PostgreSQL sync-state change.
- No Docker mount correction.
- No canonical promotion or data migration.
- No candidate/conflict workflow implementation.

## Build Report

### Changes made

- Added `master_brain_bridge.ReadOnlyCanonicalRepository`.
- Added direct exact/current/history/query retrieval with explicit authority metadata.
- Added fail-closed store and revision validation.
- Added eleven focused acceptance tests.
- Added this interface and evidence record.

### Why needed

VOX and DerekOS previously had no stable interface for distinguishing accepted Master Brain canon from raw evidence, Obsidian projections, and disposable indexes.

### Tests run

- Slice 1 focused unit/acceptance suite: 11 passed on the first run and 11 passed on the repeat run.
- Python compilation: passed.
- Git whitespace validation: passed.
- Existing Phase 1 reconciliation validator: failed outside this slice because concurrent `ingest_version: 2.0.0` fragment records (`fragment_index`, `fragment_type`, `model`, and `source_format`) are being evaluated against the strict `1.1.0` schema. Slice 1 did not create or modify those records or that schema.

### Validation evidence

Tests use a temporary canonical store with current and superseded revisions, temporary Obsidian and VOX-state sentinels, and an empty wrong-Docker-vault sentinel. Whole-tree hashes remain unchanged after retrieval.

### Remaining risks

- The production canonical JSONL store is not populated, so live canonical retrieval remains honestly unavailable.
- Direct text query is intentionally bounded and not embedding-semantic retrieval.
- VOX/DerekOS call-site wiring is not introduced in this slice; callers can explicitly invoke the package, but existing retrieval behavior remains untouched.
- A future long-running service will need a defined refresh/snapshot policy when canonical revisions are published.
- The existing Phase 1 reconciliation validator currently has a concurrent-ingestion schema/version blocker unrelated to this bridge; it must be reconciled by the ingestion owner without broadening Slice 1.

### Recommended next step

Architecture review should accept or amend this interface. After acceptance, Slice 2 may implement the one-way managed projection publisher from accepted Master Brain canonical revisions to `MasterBrain/Published/`, with collision detection and no candidate intake.

## Final change question

**Does this move VOX closer to becoming the AI Workforce Operating System?** Yes. VOX and DerekOS now have a governed read boundary that identifies what is canonical and fails rather than inventing authority.

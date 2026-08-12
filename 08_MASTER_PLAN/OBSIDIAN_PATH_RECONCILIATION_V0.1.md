# OBSIDIAN_PATH_RECONCILIATION_V0.1

**Status:** Slice 0 complete — architecture and read-only reconciliation only

**Knowledge Contract baseline:** `71b705a8093f91c84f8b2e40397919ce6e809afe`

**Inspection date:** 2026-08-12

## Build Intent Report

### Inspected

- The physical Obsidian paths referenced by VOX source and Docker Compose.
- File, Markdown, and byte counts for each existing path.
- Symlink targets, path aliases, case normalization, and OneDrive placement.
- VOX readers, writers, Docker mounts, BM25, Chroma, and PostgreSQL sync state.
- Hash overlap between physical stores.
- Existing top-level vault structure and collision risk for proposed managed subtrees.
- A non-authoritative wikilink heuristic for orphan and unresolved-link risk.

### Current architecture state

The human Obsidian vault at `C:\Users\starw\OneDrive\VOX\VOX\VOX` is the only populated curated vault among the paths used by current VOX code. Direct host readers and several writers already target it. The active Docker Compose definition does not: it resolves `../brain/vault` to an empty directory at `D:\Projects\VOX\brain\vault`. A separate historical writer target, `C:\Users\starw\OneDrive\VOX\VOX\KnowledgeGraph`, does not currently exist but would be created by runtime code if invoked.

There is also a useful host alias at `C:\Users\starw\OneDrive\VOX\brain\vault`. It is a symbolic link to the populated canonical vault. It is not the path mounted by the current `D:\Projects\VOX\vox_v4\docker-compose.yml`.

### Proposed changes

This slice changes documentation only. It declares one host path contract, one Docker mount contract, a future managed projection subtree, a future candidate inbox, and dispositions for every discovered alternate path/store.

### Files affected

- `08_MASTER_PLAN/OBSIDIAN_PATH_RECONCILIATION_V0.1.md`

### Ownership domain

Master Brain/Obsidian bridge architecture. Obsidian retains ownership of curated documentation; Master Brain retains canonical knowledge and evidence authority; VOX retains operational state.

### Risks

- Current Docker knowledge sync can index an empty path and appear healthy while containing no canonical-vault notes.
- Two runtime writer families can create a separate `KnowledgeGraph` store outside the vault.
- Multiple services can write operational material directly into warm documentation without candidate review.
- OneDrive is a synchronized transport/location, not a second source of authority; sync state cannot be used as canonical status.
- Wikilink results are heuristic because Obsidian aliases, generated schema links, and non-wikilink references may make a valid note appear orphaned.

### Verification plan

- Verify all paths with read-only filesystem inspection.
- Resolve symbolic-link targets.
- Count and hash content without modifying it.
- Trace path literals and environment-variable defaults in current VOX source.
- Confirm the proposed `MasterBrain` subtree does not collide with an existing top-level path.
- Validate the document and commit only this file.

## Authority rule

Historical evidence and canonical interpretation remain Master Brain-owned. Existing human-authored curated notes remain Obsidian-owned. A managed Obsidian projection is a presentation of Master Brain canon, never a competing canonical store. VOX operational output can enter only as a candidate until reviewed.

## Physical path reconciliation matrix

| Path/store | Role | Owner | Readers | Writers | Content count | Unique content | Authoritative status | Recommended action |
|---|---|---|---|---|---:|---|---|---|
| `C:\Users\starw\OneDrive\VOX\VOX\VOX` | Human Obsidian vault | Obsidian/human curators | `vox_brain.ObsidianReader`; Strategic Intelligence; MiroFish client; Outcome Tracker; Obsidian desktop | Humans; Outcome Tracker; parts of MiroFish | 1,056 files; 220 Markdown; 12,170,098 bytes at inventory | All 220 Markdown hashes are unique relative to the two empty/missing alternates | `CANONICAL` for curated documentation only; future managed area is `PROJECTION`; unmanaged edits are `CANDIDATE_SOURCE` | Retain as the single canonical host vault. Do not treat its location or activity as Master Brain canonical authority. |
| `C:\Users\starw\OneDrive\VOX\brain\vault` | Host filesystem alias | Same as target | Any manually configured consumer | Writes resolve to target | 389 visible non-hidden files; 220 Markdown; symlink target contains the canonical notes | No independent content; exact symbolic-link alias of canonical vault | `PROJECTION` path alias, not an independent store | Keep only as a documented compatibility alias if required. New configuration must use the canonical path, not the alias. |
| `C:\Users\starw\OneDrive\VOX\VOX\KnowledgeGraph` | Historical operational-learning target | No valid canonical owner | `KnowledgeGraphActivities.search_knowledge`; ad hoc consumers if directory is created | `KnowledgeGraphActivities.sync_insight`; `MiroFishIntelligence._store_to_obsidian`; Morning Intel-derived flows | Missing; 0 files at inventory | None | `LEGACY` configured target | Prevent future use during bridge implementation. Later route writes to the governed candidate inbox; do not create, merge, or delete in Slice 0. |
| `D:\Projects\VOX\brain\vault` | Current Compose host bind source | Deployment configuration | Docker `knowledge_sync` through `/vault` | None through current read-only mount | Existing but empty; 0 files | None | `LEGACY` empty/stale mount source | Replace the Compose source with the canonical vault contract in a later runtime slice. Preserve until that change is verified; do not populate it manually. |
| `/vault` in `knowledge_sync` container | Container read boundary | Knowledge Sync projection reader | `knowledge_sync/indexer.py` | None; mounted read-only | Mirrors `D:\Projects\VOX\brain\vault`, therefore empty under current Compose path | None | Intended `PROJECTION`; current backing is `LEGACY` | Keep `/vault` as the single container contract, but bind it to the canonical host vault read-only in the runtime wiring slice. |
| In-memory BM25 in VOX Brain | Lexical search index | VOX Brain | Retrieval consumers | Rebuilt in process by `RetrievalService` | Derived from `ObsidianReader` | No authoritative content | `DERIVED_INDEX` | Retain; label results as warm/derived and rebuild only after path wiring is accepted. |
| Chroma collection `vox_brain` | Semantic search index | Knowledge Sync | Knowledge Sync REST/search clients | `knowledge_sync/indexer.py` | Live collection contents not inferred from source inspection; configured source is currently empty Compose mount | Unknown/stale until live audit | `DERIVED_INDEX` | Retain conditionally. Do not rebuild in Slice 0; later bind source identity and canonical revision metadata. |
| PostgreSQL `knowledge_sync_state` | Delta-index bookkeeping | Knowledge Sync | Indexer | Indexer | Runtime state not inspected | No canonical content by contract | `DERIVED_INDEX` | Retain; never use it as evidence or canonical knowledge. |
| Canonical vault `10 AI Memory/` | Existing operational-output area | Obsidian surface with VOX-originated content | Obsidian and vault readers | Outcome Tracker | Included in canonical-vault count | Potentially unique operational notes | `CANDIDATE_SOURCE` / existing operational projection | Preserve. Future VOX learnings should submit to `MasterBrain/Candidates/`; do not retroactively promote these notes. |

## Readers and writers by service

| Component | Effective path | Access | Finding |
|---|---|---|---|
| `vox_brain/obsidian_reader.py` | `OBSIDIAN_VAULT_PATH`, default canonical host vault | Read | Correct host default; recursive Markdown reader; hidden directories excluded. |
| `vox_brain/retrieval.py` | Through `ObsidianReader` | Read/index | BM25 is derived and disposable. |
| `knowledge_sync/indexer.py` | `/vault` | Read/index | Container path is stable, but its current Compose backing is the empty D: drive directory. |
| `backend/app/services/outcome_tracker.py` | `OBSIDIAN_VAULT_PATH`, default canonical host vault | Write | Writes operational output under `10 AI Memory`; future flow must become candidate intake. |
| `backend/app/knowledge/mirofish.py` | Both canonical host vault and `KNOWLEDGE_GRAPH_DIR` legacy default | Read/write | One component family spans two physical targets; this is a bypass risk. |
| `backend/app/temporal/activities/knowledge_graph.py` | Hard-coded legacy `KnowledgeGraph` path | Read/write/create | Creates an independent directory on first use; must be retired or adapted in a later authorized slice. |
| `backend/app/temporal/activities/morning_intel.py` | `KNOWLEDGE_GRAPH_DIR`, same legacy default | Write-flow dependency | Participates in the legacy target family. |
| `backend/app/services/strategic_intelligence_router.py` | `OBSIDIAN_VAULT_PATH`, default canonical host vault | Read | Uses the canonical host default. |
| `backend/app/services/mirofish_client.py` | `OBSIDIAN_VAULT_PATH`, default canonical host vault | Read/write-adjacent | Uses the canonical host default. |

## Alias, duplication, and collision findings

### Path aliases and normalization

- `C:\Users\starw\OneDrive\VOX\brain\vault` is a Windows symbolic link targeting `C:\Users\starw\OneDrive\VOX\VOX\VOX`.
- `D:\Projects\VOX\brain\vault` is a normal, compressed, empty directory. It is not the OneDrive alias.
- The canonical vault itself is not a symbolic link.
- Path comparisons must use resolved absolute paths, Windows case-insensitive comparison on the host, and POSIX normalized paths inside containers. A symlink path never establishes a second vault identity.
- Vault identity must be configuration-derived and recorded separately from a mutable path; physical path alone is not a durable knowledge ID.

### OneDrive

- The canonical vault is inside OneDrive. OneDrive synchronization is transport/replication, not a second authoritative store.
- This audit proves local path identity and content, not cloud synchronization health or availability on another machine.
- Runtime writers should use atomic file replacement and conflict detection in later implementation; Slice 0 makes no changes.

### Duplicate and unique content

- The canonical host vault contains 220 Markdown notes.
- The configured `KnowledgeGraph` alternate is missing and the D: drive Compose source is empty.
- Therefore no duplicate note tree exists among those configured alternate stores at inventory time, and all populated Markdown content belongs only to the canonical host vault.
- The OneDrive `brain\vault` alias exposes the same notes and must not be counted as an independent copy.

### Orphan and broken-link heuristic

A read-only wikilink scan found 309 wikilinks across 220 notes, 159 notes with no detected inbound wikilink, and 37 distinct unresolved targets. This is a risk signal, not a migration decision: aliases, generated contract names, ordinary Markdown links, and filename ambiguity can create false positives. No note may be moved, archived, or classified as orphaned solely from this heuristic.

### Managed-subtree collision

No top-level `MasterBrain` directory exists in the canonical vault at inventory time. The proposed subtree is collision-free by exact top-level path, but it remains uncreated until the read-only bridge/publisher design is accepted.

## Future managed subtree contract

The following are reserved locations inside the canonical host vault. They are names, not directories created by this slice.

| Relative path | Classification | Allowed future content | Write authority |
|---|---|---|---|
| `MasterBrain/Published/` | `PROJECTION` | Accepted canonical knowledge rendered for humans | Dedicated Master Brain publisher only within managed regions |
| `MasterBrain/Candidates/` | `CANDIDATE_SOURCE` | Human and VOX submissions awaiting review | Authorized candidate submitters; no canonical promotion authority |
| `MasterBrain/Conflicts/` | `PROJECTION` | Human-readable conflict/review packets | Review workflow projection only |
| `MasterBrain/Archive/` | `PROJECTION` | Superseded or retired projection views | Publisher/reviewer; never the evidence archive |

The immutable Evidence Store and authoritative Canonical Store do not live in these Obsidian subtrees.

## Single-path contract

### Host

```text
VOX_OBSIDIAN_VAULT_ID = vox-primary-curated-vault
OBSIDIAN_VAULT_PATH = C:\Users\starw\OneDrive\VOX\VOX\VOX
MASTER_BRAIN_PROJECTION_RELATIVE_PATH = MasterBrain/Published
MASTER_BRAIN_CANDIDATE_RELATIVE_PATH = MasterBrain/Candidates
MASTER_BRAIN_CONFLICT_RELATIVE_PATH = MasterBrain/Conflicts
MASTER_BRAIN_ARCHIVE_RELATIVE_PATH = MasterBrain/Archive
```

All host readers must resolve the configured canonical path and record the vault ID. Host services must not fall back to `KnowledgeGraph` or any sibling directory.

### Docker

```text
host canonical vault -> /vault:ro
/vault/MasterBrain/Published -> managed projection read path
/vault/MasterBrain/Candidates -> candidate read path
```

The existing `/vault` container interface may remain. The later wiring change must bind the exact configured canonical host vault, not `D:\Projects\VOX\brain\vault`. General Knowledge Sync remains read-only. A future publisher requires a separate capability and the narrowest feasible write mount; it must not inherit a read/write mount over the whole vault.

### Fail-closed rules

- Missing canonical path: fail unavailable; do not substitute an alternate.
- Resolved path differs from the registered vault identity: deny and report drift.
- Legacy path contains new content: quarantine as a candidate source; do not auto-merge.
- Multiple configured write targets: deny governed publishing until reconciled.
- Index source differs from registered canonical vault: mark index stale/untrusted.
- Derived index availability never changes source authority.

## Disposition decisions

| Surface | Verified disposition |
|---|---|
| Populated OneDrive vault | Single canonical curated-documentation vault. |
| OneDrive `brain\vault` symlink | Compatibility alias only; no independent ownership or content. |
| Missing `KnowledgeGraph` path | Legacy configured target; future adapter/retirement required before its writer flows are enabled. |
| Empty D: drive `brain\vault` | Stale Compose bind source; later replace through configuration, not manual copying. |
| `/vault` | Preserve as container projection interface; correct its backing in a later runtime slice. |
| BM25, Chroma, PostgreSQL sync state | Derived indexes/state; retain, but never canonicalize from them. |

## Build Report

### Changes made

Added this read-only path reconciliation and single-path contract. No directory, note, index, runtime configuration, migration, or source code was changed.

### Why needed

The existing system has one populated vault, one symbolic-link alias, one empty Docker source, and one missing-but-auto-created writer target. Without an explicit disposition, bridge wiring could index the wrong path or create a second knowledge store.

### Validation evidence

- Canonical vault: 1,056 files; 220 Markdown; 12,170,098 bytes.
- Canonical visible non-hidden content through symlink: 389 files; 220 Markdown; 11,310,924 bytes.
- D: drive Compose source: 0 files.
- Legacy `KnowledgeGraph`: missing.
- OneDrive `brain\vault` resolved as a symbolic link to the canonical vault.
- All 220 canonical Markdown hashes were absent from the empty/missing alternate stores.
- No top-level `MasterBrain` collision exists.
- Source scan confirmed all listed reader/writer defaults and the Compose mount.

### Remaining risks

- Docker Knowledge Sync remains pointed at the empty D: drive source until a runtime wiring slice is authorized.
- Legacy writer code can still create `KnowledgeGraph` if executed.
- Existing operational writes bypass the future candidate-review flow.
- Chroma live content and OneDrive cloud sync health were not changed or asserted.

### Recommended next step

Authorize a read-only bridge slice that resolves Master Brain canonical records through a stable interface and exposes them to VOX/DerekOS without publishing notes or enabling bidirectional synchronization. Runtime path correction should be separately bounded and verified before any index rebuild.

## Exit criterion

Met. There is one documented canonical host vault, one container read path, one future managed projection location, one future candidate inbox, and an explicit verified disposition for every discovered alternate path/store. No physical content changed.

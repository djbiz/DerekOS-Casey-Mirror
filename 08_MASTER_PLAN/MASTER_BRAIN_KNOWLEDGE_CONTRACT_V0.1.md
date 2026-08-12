# MASTER_BRAIN_KNOWLEDGE_CONTRACT_V0.1

**Status:** Proposed architecture contract; no runtime implementation authorized

**Architecture baseline:** `887cf46f6601d7f08f19a027c159f024b4271d89`

**Core rule:** Historical/canonical truth belongs to Master Brain. Curated working knowledge belongs in Obsidian. Live operational truth belongs to VOX.

## 1. Purpose

Define one machine-auditable ownership and information-flow contract for the Master Brain, Obsidian, VOX, and DerekOS without merging their stores or creating another retrieval system.

This contract separates immutable evidence from evolving canonical interpretation:

```text
Master Brain Evidence Store
  immutable observations and provenance
              │
              ▼
Master Brain Canonical Store
  versioned current interpretation
              │
              ▼
Obsidian managed projection
  curated human-readable knowledge
              │
              ▼
VOX authorized retrieval
  operational use without ownership transfer
```

## 2. Knowledge classes and authoritative ownership

| Knowledge class | Authoritative owner | Mutability | Examples | Non-authoritative copies |
|---|---|---|---|---|
| Immutable source evidence | Master Brain Evidence Store | Append-only; source bytes immutable | conversations, source messages, external citations, execution evidence | excerpts, cached source packets |
| Canonical knowledge | Master Brain Canonical Store | Versioned; never destructive; evolves through supersession | current decisions, accepted frameworks, canonical SOP meaning, current project intent | Obsidian projections, VOX retrieval cache |
| Curated documentation | Obsidian | Human-editable within governed areas | readable SOPs, playbooks, business plans, architecture notes | BM25/Chroma chunks |
| Live operational state | VOX | Mutable under domain transaction rules | customers, WorkOrders, campaigns, leases, workflows, metrics | snapshots referenced as evidence |
| Operational learning | VOX until submitted | Append-only observations; not canonical | execution outcomes, campaign learnings, daily outcomes | Obsidian candidate inbox |
| Candidate knowledge | Master Brain Candidate Queue | Mutable workflow state; immutable submitted revisions | proposed SOP change, inferred lesson, edited strategy | Obsidian candidate note/status view |
| Embeddings and indexes | Derived subsystem only | Disposable/rebuildable | BM25 index, Chroma vectors, PostgreSQL sync state | none are truth |

No system may claim authority merely because it stores a copy, projection, embedding, cache, or search result.

## 3. Master Brain store separation

### 3.1 Evidence Store

The Evidence Store records what happened or was observed. It does not rewrite the past when current strategy changes.

Required properties:

- Immutable source bytes or immutable source hash and resolvable custody location.
- Stable evidence IDs.
- Source type, author/actor, timestamp, ingestion version, and provenance chain.
- Append-only corrections: a correction adds a new evidence record that identifies the defect; it does not mutate the original observation.
- Explicit evidence class (`D0`, `D1`, `A0`, `P0`, `I0`, `E0`, `B0`, `X0`, or later accepted extension).
- Claims of build/execution remain claims until separate execution evidence verifies them.

Evidence states are custody states, not truth judgments:

- `INGESTED`
- `QUARANTINED`
- `VERIFIED_SOURCE`
- `REDACTED_VIEW` (source retained under restricted custody)

### 3.2 Canonical Store

The Canonical Store records the current accepted interpretation of evidence.

Required properties:

- Stable knowledge ID independent of storage path or presentation.
- Monotonic canonical revision.
- Status: `CANDIDATE`, `CURRENT`, `SUPERSEDED`, `REJECTED`, `CONFLICT`, or `RETIRED`.
- Evidence IDs supporting the revision.
- Prior and successor revision links.
- Approval authority and acceptance timestamp.
- Effective interval when applicable.
- Conflict and uncertainty references.
- Projection policy and authorized consumers.

Canonical change creates a new revision. It never edits historical evidence or erases an earlier canonical state.

Example:

```text
evidence-2025: "I want X"
evidence-2026: "Replace X with Y"

KNOWLEDGE-X revision 3 → SUPERSEDED
KNOWLEDGE-Y revision 1 → CURRENT
```

## 4. Stable identity contract

### 4.1 Knowledge ID

Format:

`MBK-<DOMAIN>-<TYPE>-<ULID>`

Examples:

- `MBK-LEGACYFORGE-SOP-01K2...`
- `MBK-DEREKOS-DECISION-01K2...`
- `MBK-VOX-ARCHITECTURE-01K2...`

The ID identifies a concept across systems. It does not encode a file path, tenant database key, revision, status, or mutable title.

### 4.2 Evidence ID

Existing deterministic `source_record_id` values remain valid evidence identifiers for ingested source messages. Other evidence sources use a namespaced, deterministic or registered immutable ID.

### 4.3 Revision identity

Canonical revision identity is the tuple:

`(knowledge_id, canonical_revision)`

Every projection and retrieval result carries both values. `knowledge_id` alone means “resolve current authorized revision,” never “use whichever cached version is available.”

### 4.4 Cross-system reference

- Master Brain stores the authoritative ID and revision.
- Obsidian frontmatter stores `master_brain_id` and `master_brain_revision`.
- VOX stores references in evidence/decision records, not a duplicate canonical body unless a bounded immutable snapshot is required for execution audit.
- Derived indexes store the ID/revision as metadata and must discard stale chunks when revision changes.

## 5. Allowed flows and write authority

### 5.1 Master Brain Canonical → Obsidian projection

| Property | Rule |
|---|---|
| Initiator | Authorized Master Brain publisher |
| Source | One accepted canonical revision |
| Destination | Dedicated managed Obsidian subtree |
| Write authority | Create/update only managed projection regions |
| Idempotency | `knowledge_id + canonical_revision + content_sha256` |
| Conflict | Human change inside managed region creates conflict; publisher does not overwrite |
| Deletion | Revoke/archive projection; never delete Master Brain evidence |
| Audit | Record publisher, revision, paths, hashes, timestamp, result |

### 5.2 Obsidian edit → Master Brain candidate

| Property | Rule |
|---|---|
| Initiator | Authorized scanner, user action, or explicit submission |
| Source | Approved Obsidian subtree and exact note revision |
| Destination | Candidate Queue |
| Write authority | Candidate creation only |
| Canonical authority | None |
| Classification | `NEW`, `UPDATE`, `CONFLICT`, `SUPERSEDES`, `ANNOTATION`, `NO_CHANGE` |
| Conflict | Preserve both note content and canonical revision; no last-write-wins |
| Audit | Vault ID, relative path, note hash, submitter, base revision, timestamp |

### 5.3 VOX operational learning → candidate

| Property | Rule |
|---|---|
| Initiator | Authorized VOX service/agent with WorkOrder and lease when execution-derived |
| Source | VOX-owned operational observation/evidence |
| Destination | Candidate Queue; optional Obsidian candidate inbox projection |
| Write authority | Evidence submission and candidate creation only |
| Canonical authority | None |
| Failure behavior | Operational state remains in VOX; failed candidate submission cannot fabricate learning acceptance |
| Audit | Tenant, business, Twin, WorkOrder, lease, trace, observation/evidence IDs |

### 5.4 Master Brain canonical → VOX retrieval

| Property | Rule |
|---|---|
| Initiator | Authorized VOX/DerekOS query |
| Source | Current authorized canonical revision |
| Destination | Response/evidence packet or bounded execution snapshot |
| Write authority | Read only |
| Staleness | Requested current revision must not silently fall back to stale cache |
| Conflict | `CONFLICT` records require explicit conflict-aware response; never choose a side silently |
| Audit | Query identity, scope, returned knowledge IDs/revisions, trace |

### 5.5 VOX live operational state

VOX remains authoritative. Master Brain may retain immutable references or evidence snapshots but cannot mutate customers, campaigns, WorkOrders, leases, metrics, or runtime state.

## 6. Candidate-review queue design

This section defines the queue; it does not deploy it.

### 6.1 Candidate record

```json
{
  "candidate_id": "MBC-01K2...",
  "candidate_revision": 1,
  "candidate_type": "NEW|UPDATE|CONFLICT|SUPERSEDES|ANNOTATION",
  "source_system": "obsidian|vox",
  "source_identity": {},
  "proposed_knowledge_id": null,
  "base_canonical_revision": null,
  "submitted_content_hash": "...",
  "evidence_ids": [],
  "status": "SUBMITTED",
  "submitted_by": "...",
  "submitted_at": "...",
  "review_history": []
}
```

### 6.2 Queue states

`SUBMITTED → TRIAGED → EVIDENCE_REQUIRED | REVIEW_READY → ACCEPTED | REJECTED | CONFLICT_OPEN | DUPLICATE`

Acceptance creates a new canonical revision through the canonicalization service. Queue state alone never changes canon.

### 6.3 Review invariants

- Submitted candidate revisions are immutable.
- Review comments append; they do not rewrite source content.
- Candidate submitters cannot self-approve unless policy explicitly grants that role.
- Assistant or agent confidence cannot substitute for evidence.
- Cross-tenant candidates and evidence fail closed.
- A candidate based on a stale canonical revision becomes `CONFLICT_OPEN` or requires rebase; it is not auto-merged.

## 7. Existing component classification

| Component | Current classification | Contract role | Required disposition |
|---|---|---|---|
| Master Brain `00_RAW_ARCHIVE` and evidence records | `AUTHORITATIVE` | Evidence Store | Preserve immutable custody |
| Master Brain future accepted canonical records | `AUTHORITATIVE` | Canonical Store | Implement versioned canonicalization before publishing |
| Obsidian host vault `...\VOX\VOX\VOX` | `AUTHORITATIVE` for existing human-authored curated notes; `PROJECTION` for future managed notes | Warm surface | Partition managed, candidate, and unmanaged areas |
| `vox_brain.ObsidianReader` | `PROJECTION_READER` | Read warm notes | Keep; add source type/revision metadata later |
| VOX Brain in-memory BM25 | `DERIVED_INDEX` | Local lexical retrieval | Keep; rebuildable, never canonical |
| Knowledge Sync Chroma collection `vox_brain` | `DERIVED_INDEX` | Semantic warm-note retrieval | Keep conditionally after vault path reconciliation |
| PostgreSQL `knowledge_sync_state` | `DERIVED_INDEX_STATE` | Delta-index bookkeeping | Keep; never evidence or canon |
| Docker mount `../brain/vault:/vault:ro` | `LEGACY/UNKNOWN` | Possible alternate vault | Reconcile physical identity before relying on it |
| `...\VOX\VOX\KnowledgeGraph` | `LEGACY/UNKNOWN` | Alternate runtime writer target | Inventory and disposition; no automatic merge |
| Outcome Tracker `10 AI Memory` writes | `OPERATIONAL_PROJECTION` | Hot-to-warm observation | Route to candidate inbox eventually |
| MiroFish daily-learning writes | `OPERATIONAL_PROJECTION` | Hot-to-warm observation | Route to candidate inbox eventually |
| Logseq `knowledge.graph` MCP | `SEPARATE_PROJECTION/TOOL` | Linked graph workspace | Do not repurpose as Master Brain |
| AppFlowy `workspace.knowledge` MCP | `SEPARATE_PROJECTION/TOOL` | Workspace knowledge | Do not repurpose as Master Brain |

## 8. Conflict behavior

| Conflict | Required behavior |
|---|---|
| Canonical revision changed after projection | Mark projection stale; republish only if managed content is unchanged |
| Human edited managed projection | Open candidate/conflict; preserve both versions |
| Obsidian note references missing knowledge ID | Quarantine candidate; do not create replacement canon automatically |
| Two Obsidian notes claim same current knowledge ID | Conflict; no winner by modification time |
| VOX observation contradicts canonical knowledge | Preserve operational fact, create conflict candidate, do not mutate canon |
| Search indexes disagree | Rebuild from named source/revision; index rank never resolves truth |
| Evidence contradicts evidence | Preserve both; canonicalization must acknowledge conflict |
| Tenant/scope mismatch | Deny without partial data leakage |

## 9. Retrieval response contract

Every knowledge response must distinguish:

- `source_temperature`: `HOT`, `WARM`, or `COLD_DEEP`
- `authority_class`: `AUTHORITATIVE`, `PROJECTION`, or `DERIVED_INDEX`
- `knowledge_id` and `canonical_revision` when canonical
- `evidence_ids` when provenance is requested
- `canonical_status`
- `conflict_status`
- `retrieved_from` and `indexed_from`
- `as_of`

A Chroma/BM25 result is a locator. The final response authority derives from the resolved source record, not the index hit.

## 10. Security and governance

- Runtime flows require explicit identity, tenant, capability, resource scope, and active lease where execution authority applies.
- Knowledge visibility is filtered before retrieval, not merely after ranking.
- Raw/deep evidence may be more restricted than its canonical summary.
- Obsidian managed projection publishing uses a dedicated capability distinct from general vault writes.
- Candidate submission and canonical acceptance are separate capabilities.
- Every write carries trace and audit identity.
- No knowledge record authorizes a WorkOrder or external action by itself.

## 11. Migration-impact matrix

| Existing surface | Can remain unchanged now? | Adapter/change eventually required | Retirement candidate |
|---|---:|---|---:|
| Master Brain Evidence Store/ingest | Yes | Expose stable evidence lookup behind read API | No |
| Master Brain canonical directories | Yes, until canonicalization implementation | Add canonical revision store and resolver | No |
| Obsidian vault content | Yes | Establish managed projection and candidate inbox subtrees | No |
| `ObsidianReader` | Yes | Add projection metadata and optionally query Master Brain as separate provider | No |
| VOX Brain BM25 | Yes | Tag results as warm/derived and resolve authority | No |
| Knowledge Sync Chroma | Yes if current mount is correct | Reconcile mount; store knowledge ID/revision metadata; stale revision deletion | No |
| PostgreSQL sync state | Yes | Replace MD5 with stronger content identity when touched; add vault identity | No |
| Docker `../brain/vault` path | No assumption allowed | Resolve to canonical vault or explicitly isolated vault | Possibly |
| `KnowledgeGraph` alternate path | No assumption allowed | Inventory, classify, and migrate only by explicit disposition | Yes, if duplicate |
| Outcome Tracker vault writer | Yes temporarily | Write to governed operational/candidate subtree and submit candidate references | No |
| MiroFish vault writer | Yes temporarily | Same candidate path and provenance requirements | No |
| Logseq/AppFlowy knowledge tools | Yes | Keep ownership distinct and label projections | No |
| Direct bulk raw-corpus retrieval | Not present and must not be added | Use provenance API for bounded deep queries | N/A |

## 12. Acceptance tests for future implementation

- Evidence remains unchanged when canon supersedes a concept.
- Canonical revisions are monotonic and resolvable historically.
- Obsidian projections are idempotent by ID/revision/hash.
- Human edits cannot be overwritten silently.
- Obsidian and VOX submissions create candidates only.
- Operational state remains VOX-owned after candidate acceptance.
- BM25/Chroma can be deleted and rebuilt without knowledge loss.
- Stale/missing index metadata cannot masquerade as current canonical knowledge.
- Conflicts are returned explicitly.
- Tenant/scope mismatch is denied.
- No raw corpus bulk copy is created.

## 13. Explicit exclusions

- No vault content migration.
- No store merge.
- No Chroma rebuild or embedding change.
- No VOX runtime modification.
- No Master Brain API/MCP implementation.
- No candidate queue deployment.
- No canonical promotion.

## 14. Next decision

Architecture Board review should accept or amend this contract, then authorize only Bridge Slice 0: authority and physical path reconciliation. No runtime bridge implementation should begin until the canonical vault, managed subtree, candidate inbox, and legacy path dispositions are explicit.

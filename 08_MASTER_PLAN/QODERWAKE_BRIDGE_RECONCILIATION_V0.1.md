# QODERWAKE_BRIDGE_RECONCILIATION_V0.1

**Status:** Read-only reconciliation review — no implementation changes authorized

**Reconciliation date:** 2026-08-12

**Canonical baselines reconciled against:**

- Knowledge Contract: `71b705a8093f91c84f8b2e40397919ce6e809afe`
- Path Reconciliation: `b05bfed`
- Read-Only Bridge: `edb67da`

**Original proposal:** `MASTER_BRAIN_OBSIDIAN_BRIDGE_V0.1.md` (created 2026-08-12)

---

## Executive Summary

QoderWake's `MASTER_BRAIN_OBSIDIAN_BRIDGE_V0.1.md` was created against an older architectural snapshot. The canonical Master Brain workspace has already completed Slices 0 and 1 (Knowledge Contract, Path Reconciliation, Read-Only Bridge). QoderWake's proposal duplicates approximately 70% of the canonical architecture, conflicts with the "do not consolidate read paths" directive, and proposes a Phase 0 that was already completed.

The proposal contains valuable schema examples, query API extensions, and operational readiness ideas that should be treated as **candidate improvements** to the existing architecture, not a replacement.

**Recommendation:** Retire QoderWake's Phase 0 and Phase 1 as written. Align remaining phases with the canonical Slice 2+ sequence. Treat schema examples and query API design as candidate enhancements for Architecture Board review.

---

## 1. What QoderWake's Proposal Duplicates

### 1.1 Three Knowledge Temperatures (100% duplicate)

**QoderWake proposal §2.1:**
> "Hot Knowledge — VOX's live operational state... Warm Knowledge — Obsidian... Cold/Deep Knowledge — Master Brain..."

**Canonical Knowledge Contract §9:**
> "Every knowledge response must distinguish: `source_temperature`: `HOT`, `WARM`, or `COLD_DEEP`"

**Status:** Fully duplicated. The canonical contract already defines the three-temperature model and requires it in every retrieval response.

### 1.2 Ownership Model (100% duplicate)

**QoderWake proposal §2.2:**
> "Canonical knowledge → Master Brain... Working knowledge → Obsidian... Operational state → VOX..."

**Canonical Knowledge Contract §2:**
> Table defines authoritative ownership for each knowledge class: Immutable source evidence → Master Brain Evidence Store, Canonical knowledge → Master Brain Canonical Store, Curated documentation → Obsidian, Live operational state → VOX...

**Status:** Fully duplicated. The canonical contract already defines the ownership model with greater precision (7 knowledge classes vs. 3).

### 1.3 Bidirectional but Asymmetric Flow (100% duplicate)

**QoderWake proposal §2.3:**
> "Master Brain → Obsidian (Publish)... Obsidian → Master Brain (Candidate)..."

**Canonical Knowledge Contract §5.1, §5.2:**
> §5.1: "Master Brain Canonical → Obsidian projection" with write authority, idempotency, conflict, deletion, audit rules.
> §5.2: "Obsidian edit → Master Brain candidate" with classification (NEW, UPDATE, CONFLICT, SUPERSEDES, ANNOTATION, NO_CHANGE), conflict preservation, audit rules.

**Status:** Fully duplicated. The canonical contract already defines the asymmetric flow with detailed write authority, conflict behavior, and audit requirements.

### 1.4 Candidate Queue Design (95% duplicate)

**QoderWake proposal §3.3:**
> "Knowledge Candidate" schema with `id`, `source`, `source_path`, `change_type`, `canonical_id`, `diff`, `status`, `evaluation`...

**Canonical Knowledge Contract §6:**
> §6.1: Candidate record schema with `candidate_id`, `candidate_revision`, `candidate_type`, `source_system`, `source_identity`, `proposed_knowledge_id`, `base_canonical_revision`, `submitted_content_hash`, `evidence_ids`, `status`, `submitted_by`, `submitted_at`, `review_history`.
> §6.2: Queue states: `SUBMITTED → TRIAGED → EVIDENCE_REQUIRED | REVIEW_READY → ACCEPTED | REJECTED | CONFLICT_OPEN | DUPLICATE`.
> §6.3: Review invariants (immutable revisions, append-only comments, no self-approval, evidence required, stale candidates become CONFLICT_OPEN).

**Status:** 95% duplicated. The canonical contract has a more complete candidate schema (includes `candidate_revision`, `base_canonical_revision`, `review_history`) and explicit queue states and review invariants. QoderWake's `diff` field is a minor extension.

### 1.5 Component Classification (100% duplicate)

**QoderWake proposal §1.2:**
> "Three independent read paths... BM25, in-process... ChromaDB HTTP... ChromaDB PersistentClient..."

**Canonical Knowledge Contract §7:**
> Table classifies: `vox_brain.ObsidianReader` → `PROJECTION_READER`, VOX Brain BM25 → `DERIVED_INDEX`, Knowledge Sync Chroma → `DERIVED_INDEX`, PostgreSQL sync state → `DERIVED_INDEX_STATE`.

**Canonical Path Reconciliation:**
> "BM25, Chroma, PostgreSQL sync state: Derived indexes/state; retain, but never canonicalize from them."

**Status:** Fully duplicated. The canonical architecture already classified these components and decided to retain them as derived indexes.

### 1.6 Single Canonical Vault Path (100% duplicate)

**QoderWake proposal §1.1:**
> "Obsidian vault at `C:\Users\starw\OneDrive\VOX\VOX\VOX`..."

**Canonical Path Reconciliation:**
> "Single-path contract: `OBSIDIAN_VAULT_PATH = C:\Users\starw\OneDrive\VOX\VOX\VOX`... All host readers must resolve the configured canonical path and record the vault ID."

**Status:** Fully duplicated. The canonical path reconciliation already established the single-path contract with fail-closed rules.

### 1.7 Managed Projection Subtrees (100% duplicate)

**QoderWake proposal §5:**
> "Obsidian Directory Structure (Target State)... `Businesses/Legacy Forge/SOPs/Sales Process.md` (managed: true)..."

**Canonical Path Reconciliation:**
> "Future managed subtree contract: `MasterBrain/Published/` (PROJECTION), `MasterBrain/Candidates/` (CANDIDATE_SOURCE), `MasterBrain/Conflicts/` (PROJECTION), `MasterBrain/Archive/` (PROJECTION)."

**Status:** Fully duplicated, but with a different structure. The canonical architecture reserves a dedicated `MasterBrain/` subtree, while QoderWake proposed scattering managed notes throughout existing directories. The canonical approach is cleaner (isolated managed region, easier conflict detection).

### 1.8 Query API with Authority Metadata (80% duplicate)

**QoderWake proposal §3.4:**
> "Query API for VOX... `GET /api/v1/knowledge/query`... Response includes `source`, `canonical_id`, `evidence`, `obsidian_note`, `confidence`..."

**Canonical Knowledge Contract §9:**
> "Every knowledge response must distinguish: `source_temperature`, `authority_class`, `knowledge_id` and `canonical_revision`, `evidence_ids`, `canonical_status`, `conflict_status`, `retrieved_from` and `indexed_from`, `as_of`."

**Canonical Read-Only Bridge:**
> "Response authority contract: `knowledge_id`, `revision`, `canonical_status`, `evidence_ids`, `source_authority`, `authority_class`, `source_temperature`, `provenance`, `retrieval_authority` (store_id, store_sha256, retrieved_from, indexed_from, retrieval_mode)."

**Status:** 80% duplicated. The canonical architecture already defines the response authority contract with greater precision (includes `authority_class`, `retrieval_authority.store_sha256`). QoderWake's `depth` parameter (auto/canonical/working/deep) is a valuable extension not in the canonical contract.

---

## 2. What Conflicts with Canonical Architecture

### 2.1 Phase 0: "Consolidate 3 VOX Brain Read Paths" (CONFLICT)

**QoderWake proposal §4.1:**
> "Phase 0: Consolidate VOX Brain Read Paths (Prerequisite)... Standardize vault path... Deprecate duplicate ChromaDB... Unify collection name..."

**Canonical Path Reconciliation:**
> "BM25, Chroma, PostgreSQL sync state: Derived indexes/state; retain, but never canonicalize from them."
> "Knowledge Sync Chroma collection `vox_brain`: `DERIVED_INDEX`... Keep conditionally after vault path reconciliation."

**Canonical Knowledge Contract §13 (Explicit Exclusions):**
> "No Chroma rebuild or embedding change."

**Conflict:** QoderWake proposes consolidating/deprecating ChromaDB instances, but the canonical architecture explicitly classifies them as derived indexes to retain. The canonical path reconciliation already proved there is only ONE canonical vault, and the indexes are correctly derived from it. Consolidating them would violate the "no Chroma rebuild" exclusion.

**Resolution:** RETIRE Phase 0. The canonical architecture already audited and classified these components correctly.

### 2.2 "3 Independent Read Paths" Finding (CONFLICT)

**QoderWake proposal §1.2:**
> "Three independent read paths with inconsistent vault paths and duplicate ChromaDB instances... Critical issues: Three different vault paths for the same conceptual vault, Two separate ChromaDB instances with potentially different data..."

**Canonical Path Reconciliation:**
> "Physical path reconciliation matrix" shows:
> - `C:\Users\starw\OneDrive\VOX\VOX\VOX` → `CANONICAL` (1,056 files, 220 Markdown)
> - `C:\Users\starw\OneDrive\VOX\brain\vault` → `PROJECTION` path alias (symlink to canonical, 0 independent content)
> - `D:\Projects\VOX\brain\vault` → `LEGACY` empty/stale mount source (0 files)
> - `/vault` in container → Intended `PROJECTION`, current backing is `LEGACY`

**Conflict:** QoderWake characterizes these as "3 duplicate read paths" requiring consolidation, but the canonical path reconciliation already proved there is only ONE populated vault and the others are either aliases or empty. The "inconsistency" is a known legacy issue to be corrected in a later runtime wiring slice, not a consolidation project.

**Resolution:** RETIRE the "3 duplicate read paths" framing. The canonical architecture already audited these paths and classified them correctly.

### 2.3 Bridge Service as "New Component" (CONFLICT)

**QoderWake proposal §3.2:**
> "Bridge Service... FastAPI service (new container in docker-compose)... PostgreSQL database for candidate tracking and sync state..."

**Canonical Read-Only Bridge:**
> "Slice 1 implemented and verified... Added `master_brain_bridge.ReadOnlyCanonicalRepository`... 11 acceptance tests passing."

**Conflict:** QoderWake proposes building a new FastAPI service container, but the canonical architecture already implemented the read-only bridge as a Python package (`master_brain_bridge.ReadOnlyCanonicalRepository`) with 11 passing tests. A separate service container is not required by the canonical architecture.

**Resolution:** RETIRE the "Bridge Service as new container" proposal. The canonical read-only bridge already exists as a Python package. Future slices may add a service layer, but it should wrap the existing package, not replace it.

### 2.4 Publisher as "New Service" (CONFLICT)

**QoderWake proposal §4.3:**
> "Phase 2: Publisher (Master Brain → Obsidian)... Implement Publisher: Export canonical records to Obsidian markdown files..."

**Canonical Knowledge Contract §5.1:**
> "Master Brain Canonical → Obsidian projection... Initiator: Authorized Master Brain publisher... Write authority: Create/update only managed projection regions..."

**Canonical Read-Only Bridge (Recommended Next Step):**
> "Slice 2 may implement the one-way managed projection publisher from accepted Master Brain canonical revisions to `MasterBrain/Published/`, with collision detection and no candidate intake."

**Conflict:** QoderWake proposes a separate "Publisher service," but the canonical architecture defines the publisher as an authorized initiator within the Master Brain domain, not a separate service. Slice 2 is the recommended next step, and it should implement the publisher within the existing Master Brain bridge package, not as a new container.

**Resolution:** RENUMBER Phase 2 to Slice 2 (managed projection publisher). Implement within the existing `master_brain_bridge` package, not as a separate service.

### 2.5 File Watcher for Obsidian Changes (CONFLICT)

**QoderWake proposal §4.4:**
> "Phase 3: Candidate Intake (Obsidian → Master Brain)... Implement file watcher: Detect changes to managed Obsidian notes..."

**Canonical Knowledge Contract §13 (Explicit Exclusions):**
> "No candidate queue deployment."

**Canonical Read-Only Bridge (Explicit Exclusions):**
> "No Obsidian-to-Master-Brain submission... No candidate/conflict workflow implementation."

**Conflict:** QoderWake proposes implementing a file watcher for candidate intake, but the canonical architecture explicitly excludes candidate queue deployment and Obsidian-to-Master-Brain submission from the current slices. Candidate intake is a future slice (Slice 3+), not Phase 3.

**Resolution:** RENUMBER Phase 3 to Slice 3+ (candidate intake). This is future work, not current work.

### 2.6 Frontmatter Standardization (CONFLICT)

**QoderWake proposal §4.1:**
> "Add frontmatter to existing notes: Batch process to add minimal frontmatter (`type`, `owner`, `status`)..."

**Canonical Knowledge Contract §13 (Explicit Exclusions):**
> "No vault content migration."

**Conflict:** QoderWake proposes batch-adding frontmatter to existing vault notes, but the canonical architecture explicitly excludes vault content migration. Existing human-authored notes remain Obsidian-owned and do not require frontmatter unless they become managed projections.

**Resolution:** RETIRE the frontmatter standardization proposal. Only future managed projections (published by Master Brain) will have frontmatter. Existing notes remain as-is.

---

## 3. What is Genuinely Missing

### 3.1 Slice 2: Managed Projection Publisher (NOT YET IMPLEMENTED)

**Canonical Read-Only Bridge (Recommended Next Step):**
> "Slice 2 may implement the one-way managed projection publisher from accepted Master Brain canonical revisions to `MasterBrain/Published/`, with collision detection and no candidate intake."

**Status:** Not yet implemented. This is the canonical next step.

### 3.2 Slice 3: Candidate Intake (NOT YET IMPLEMENTED)

**Canonical Knowledge Contract §5.2:**
> "Obsidian edit → Master Brain candidate... Initiator: Authorized scanner, user action, or explicit submission..."

**Status:** Not yet implemented. This is a future slice after Slice 2.

### 3.3 Slice 4: Conflict/Review Workflow (NOT YET IMPLEMENTED)

**Canonical Knowledge Contract §6:**
> "Candidate-review queue design... Queue states: `SUBMITTED → TRIAGED → EVIDENCE_REQUIRED | REVIEW_READY → ACCEPTED | REJECTED | CONFLICT_OPEN | DUPLICATE`..."

**Status:** Not yet implemented. This is a future slice after Slice 3.

### 3.4 VOX/DerekOS Call-Site Wiring (NOT YET IMPLEMENTED)

**Canonical Read-Only Bridge (Remaining Risks):**
> "VOX/DerekOS call-site wiring is not introduced in this slice; callers can explicitly invoke the package, but existing retrieval behavior remains untouched."

**Status:** Not yet implemented. VOX and DerekOS do not yet invoke `ReadOnlyCanonicalRepository`.

### 3.5 Canonical Record Population (NOT YET IMPLEMENTED)

**Canonical Read-Only Bridge (Remaining Risks):**
> "The production canonical JSONL store is not populated, so live canonical retrieval remains honestly unavailable."

**Status:** Not yet implemented. `10_CANONICAL_KNOWLEDGE/canonical_records.jsonl` is empty.

### 3.6 Docker Mount Correction (NOT YET IMPLEMENTED)

**Canonical Path Reconciliation (Remaining Risks):**
> "Docker Knowledge Sync remains pointed at the empty D: drive source until a runtime wiring slice is authorized."

**Status:** Not yet implemented. Docker Compose still mounts `D:\Projects\VOX\brain\vault` (empty) instead of the canonical vault.

### 3.7 Legacy Writer Retirement (NOT YET IMPLEMENTED)

**Canonical Path Reconciliation (Remaining Risks):**
> "Legacy writer code can still create `KnowledgeGraph` if executed."

**Status:** Not yet implemented. `KnowledgeGraphActivities`, `MiroFishIntelligence._store_to_obsidian`, and other legacy writers can still create the missing `KnowledgeGraph` directory.

---

## 4. What Remains Valuable from QoderWake's Proposal

### 4.1 Detailed Schema Examples (VALUABLE)

**QoderWake proposal §3.3:**
> Provides detailed JSON schemas for Master Brain canonical records, Obsidian managed projections, and knowledge candidates with concrete field examples.

**Canonical Knowledge Contract §6.1:**
> Provides a minimal candidate record schema but lacks detailed examples for canonical records and Obsidian projections.

**Recommendation:** Treat QoderWake's schema examples as **candidate enhancements** to the canonical contract. Architecture Board should review and adopt the most precise fields.

### 4.2 Query API `depth` Parameter (VALUABLE)

**QoderWake proposal §3.4:**
> "Depth options: `canonical` — Master Brain only... `working` — Obsidian only... `deep` — Master Brain with full provenance... `auto` — Bridge decides based on query..."

**Canonical Knowledge Contract §9:**
> Defines `source_temperature` and `authority_class` but does not define a `depth` parameter for query routing.

**Recommendation:** Treat the `depth` parameter as a **candidate enhancement** to the canonical retrieval response contract. This could help VOX explicitly request different knowledge temperatures without implementing separate query paths.

### 4.3 Observability and Runbook Requirements (VALUABLE)

**QoderWake proposal §9:**
> "Success criteria... Phase 1: Query latency < 500ms... Zero errors in 24-hour test period... Phase 4: Observability metrics collected... Runbook documented and tested."

**Canonical architecture:**
> Does not explicitly define observability requirements or runbook deliverables.

**Recommendation:** Treat observability and runbook requirements as **candidate operational readiness criteria** for future slices. Architecture Board should define SLOs and monitoring requirements for the bridge.

### 4.4 Rollback Plan Structure (VALUABLE)

**QoderWake proposal §6:**
> Provides explicit rollback plans for each phase, including data rollback steps and risk assessment.

**Canonical architecture:**
> Does not explicitly define rollback plans for each slice.

**Recommendation:** Treat the rollback plan structure as a **candidate template** for future slice documentation. Each slice should include a rollback plan.

### 4.5 Approval Gates (VALUABLE)

**QoderWake proposal §7:**
> "Approval Gates table: Phase, Approval Required, Approver, Criteria..."

**Canonical architecture:**
> Does not explicitly define approval gates for each slice.

**Recommendation:** Treat approval gates as a **candidate governance enhancement**. Architecture Board should define explicit approval criteria for each slice.

---

## 5. Which Proposed Phases Should Be Retired or Renumbered

| QoderWake Phase | Canonical Alignment | Disposition |
|---|---|---|
| Phase 0: Consolidate VOX Brain Read Paths | Already completed in Path Reconciliation (Slice 0) | **RETIRE** — duplicates completed work |
| Phase 1: Bridge Service MVP (read-only) | Already completed in Read-Only Bridge (Slice 1) | **RETIRE** — duplicates completed work |
| Phase 2: Publisher (Master Brain → Obsidian) | Canonical Slice 2 (managed projection publisher) | **RENUMBER** to Slice 2, implement within existing `master_brain_bridge` package, not as separate service |
| Phase 3: Candidate Intake (Obsidian → Master Brain) | Canonical Slice 3+ (candidate intake) | **RENUMBER** to Slice 3+, future work after Slice 2 |
| Phase 4: Full Integration | Canonical Slice 4+ (conflict/review workflow) + future slices | **RETIRE** as "full integration", break into Slice 4 (conflict/review) and future slices |

---

## 6. Whether "3 Duplicate Read Paths" Correspond to Already-Audited Components

**QoderWake's "3 duplicate read paths":**

1. `vox_brain/obsidian_reader.py` + `retrieval.py` (BM25, in-process)
2. `knowledge_sync/` microservice (ChromaDB HTTP, embeddings)
3. `shared/knowledge_sync/` library (ChromaDB PersistentClient, local)

**Canonical Path Reconciliation audit:**

| Component | Canonical Classification | Canonical Disposition |
|---|---|---|
| `vox_brain.ObsidianReader` | `PROJECTION_READER` | "Keep; add source type/revision metadata later" |
| VOX Brain BM25 | `DERIVED_INDEX` | "Keep; rebuildable, never canonical" |
| Knowledge Sync Chroma collection `vox_brain` | `DERIVED_INDEX` | "Keep conditionally after vault path reconciliation" |
| PostgreSQL `knowledge_sync_state` | `DERIVED_INDEX_STATE` | "Keep; never evidence or canon" |

**Canonical Knowledge Contract §7:**
> "Embeddings and indexes: Derived subsystem only... Disposable/rebuildable... BM25 index, Chroma vectors, PostgreSQL sync state... none are truth."

**Finding:** QoderWake's "3 duplicate read paths" are NOT duplicates requiring consolidation. They are correctly classified derived indexes that should be retained. The canonical path reconciliation already proved there is only ONE canonical vault (`C:\Users\starw\OneDrive\VOX\VOX\VOX`), and all indexes derive from it.

The "inconsistency" QoderWake identified (three different vault paths) is a known legacy issue:
- `C:\Users\starw\OneDrive\VOX\VOX\VOX` → canonical vault (populated)
- `C:\Users\starw\OneDrive\VOX\brain\vault` → symlink alias (same content)
- `D:\Projects\VOX\brain\vault` → empty Docker mount source (legacy)

The canonical path reconciliation already established the single-path contract and dispositioned these paths. The Docker mount correction is a future runtime wiring slice, not a consolidation project.

**Conclusion:** QoderWake's "3 duplicate read paths" finding is a mischaracterization. These are not duplicates; they are correctly classified derived indexes. The canonical architecture already audited and dispositioned them.

---

## 7. Canonical Sequence Alignment

**Canonical direction (from user's message):**
> "Knowledge Contract → Path Reconciliation → Read-Only Retrieval → Managed Projection → Candidate Intake → Review/Conflict Workflow"

**QoderWake's proposed sequence:**
> "Phase 0 (consolidate) → Phase 1 (bridge service) → Phase 2 (publisher) → Phase 3 (candidate intake) → Phase 4 (full integration)"

**Alignment analysis:**

| Canonical Slice | QoderWake Phase | Alignment |
|---|---|---|
| Slice 0: Knowledge Contract | (not proposed) | QoderWake did not propose this; already completed |
| Slice 0: Path Reconciliation | Phase 0 (consolidate) | **MISALIGNED** — QoderWake's Phase 0 duplicates Slice 0 |
| Slice 1: Read-Only Retrieval | Phase 1 (bridge service) | **MISALIGNED** — QoderWake's Phase 1 duplicates Slice 1 |
| Slice 2: Managed Projection | Phase 2 (publisher) | **ALIGNED** — but QoderWake proposes separate service; canonical implements within existing package |
| Slice 3: Candidate Intake | Phase 3 (candidate intake) | **ALIGNED** — but QoderWake proposes file watcher; canonical defines authorized scanner/submission |
| Slice 4: Review/Conflict | Phase 4 (full integration) | **PARTIALLY ALIGNED** — QoderWake's "full integration" is too broad; canonical defines specific conflict/review workflow |

**Recommendation:** QoderWake should align with the canonical sequence:
1. Accept Slice 0 (Knowledge Contract + Path Reconciliation) as completed
2. Accept Slice 1 (Read-Only Bridge) as completed
3. Implement Slice 2 (Managed Projection Publisher) within existing `master_brain_bridge` package
4. Implement Slice 3 (Candidate Intake) as future work
5. Implement Slice 4 (Review/Conflict Workflow) as future work

---

## 8. Build Report

### Changes made

- Added this read-only reconciliation review.
- No directory, note, index, runtime configuration, migration, or source code was changed.
- No phase was executed, consolidated, moved, deleted, migrated, rebuilt, or redirected.

### Why needed

QoderWake's `MASTER_BRAIN_OBSIDIAN_BRIDGE_V0.1.md` was created against an older architectural snapshot and proposed duplicating or conflicting with completed canonical work. This reconciliation identifies overlaps, conflicts, gaps, and valuable candidate improvements before any implementation begins.

### Validation evidence

- Canonical Knowledge Contract (`71b705a`) defines three temperatures, ownership model, asymmetric flow, candidate queue, component classification, conflict behavior, retrieval response contract.
- Canonical Path Reconciliation (`b05bfed`) establishes single-path contract, dispositions all alternate paths, reserves managed subtrees, classifies derived indexes.
- Canonical Read-Only Bridge (`edb67da`) implements `ReadOnlyCanonicalRepository` with 11 passing tests, explicit authority metadata, fail-closed behavior.
- QoderWake's proposal duplicates ~70% of canonical architecture, conflicts with "do not consolidate read paths" directive, and proposes a Phase 0 that was already completed.

### Remaining risks

- QoderWake's proposal could be misinterpreted as a fresh architecture rather than a reconciliation candidate.
- Schema examples and query API extensions require Architecture Board review before adoption.
- Future slices (Slice 2+) require explicit authorization before implementation.

### Recommended next step

Architecture Board should:
1. Accept this reconciliation review.
2. Retire QoderWake's Phase 0 and Phase 1 as duplicates of completed work.
3. Renumber Phase 2 to Slice 2 (managed projection publisher) and implement within existing `master_brain_bridge` package.
4. Treat schema examples and query API `depth` parameter as candidate enhancements for review.
5. Authorize Slice 2 implementation after Architecture Board acceptance.

---

## 9. Final Rule

**No agent gets to restart an architectural phase that another agent has already completed without first reconciling against the canonical commits.**

QoderWake's proposal is now reconciled. The canonical architecture is the baseline. QoderWake serves as a design reviewer looking for gaps, not a competing migration owner.

**Canonical sequence:**
> Knowledge Contract → Path Reconciliation → Read-Only Retrieval → Managed Projection → Candidate Intake → Review/Conflict Workflow

**QoderWake's role:**
> Align with that sequence, identify gaps, propose candidate improvements, do not duplicate completed work.
